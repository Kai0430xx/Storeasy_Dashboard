from pathlib import Path
import json, re, subprocess, datetime, tempfile, struct, zlib

root = Path(__file__).resolve().parents[1]
assets = {}

assets['functions/package.json'] = r'''
{
  "name": "storeasy-notifications",
  "private": true,
  "type": "module",
  "main": "index.js",
  "engines": {"node": "22"},
  "dependencies": {
    "firebase-admin": "13.10.0",
    "firebase-functions": "6.6.0",
    "web-push": "3.6.7"
  }
}
'''

assets['functions/notification-domain.js'] = r'''
import {ECDH} from 'node:crypto';

export const roles = ['admin','supervisor','manager'];
export const enabled = p => roles.includes(p?.role);
export const globalProfile = p => ['admin','supervisor'].includes(p?.role);
export const intersects = (a=[],b=[]) => a.some(id=>b.includes(id));
export const millis = v => Number(
  v?.toMillis?.() ??
  (v?.seconds!=null
    ? v.seconds*1000+Math.floor((v.nanoseconds||0)/1e6)
    : v||0)
)||0;

export const day = () => new Intl.DateTimeFormat('en-CA',{
  timeZone:'Asia/Taipei',
  year:'numeric',
  month:'2-digit',
  day:'2-digit'
}).format(new Date());

export function workVisible(task,uid,p,assignment){
  return enabled(p)&&(
    globalProfile(p)||
    task.createdBy===uid||
    intersects(task.branchIds,p.branchIds)||
    !!assignment
  );
}

export const workNotificationVisible = (
  task,uid,p,assignment=false
) => enabled(p)&&(
  globalProfile(p)
    ? (task.directAssigneeIds||[]).includes(uid)||assignment
    : workVisible(task,uid,p,assignment)
);

export const waitingNotificationVisible = (row,uid,p) =>
  p?.role==='manager'&&intersects(row.branchIds,p.branchIds);

export const calendarDate = s =>
  /^20\d{2}-\d{2}-\d{2}$/.test(s||'')&&
  !Number.isNaN(Date.parse(s+'T00:00:00Z'))&&
  new Date(s+'T00:00:00Z').toISOString().slice(0,10)===s;

export const vacancyKey = u => JSON.stringify([
  u.branchId,u.code,u.vacantSince,u.lastEventId,u.lastEventDate
]);

export function workUnread(tasks,reads,uid){
  const keys=[];
  for(const task of tasks){
    const threads=[];
    for(const [thread,signals] of Object.entries(task.signals||{})){
      if(task.deleted&&thread!=='main')continue;
      const unseen=Object.entries(signals).filter(
        ([actor,time])=>
          actor!==uid&&
          millis(time)>millis(reads[task.id]?.seen?.[thread])
      );
      if(unseen.length){
        threads.push([
          thread,
          unseen.map(([actor,time])=>[actor,millis(time)]).sort()
        ]);
      }
    }
    if(threads.length){
      keys.push(JSON.stringify([task.id,threads.sort()]));
    }
  }
  return {count:keys.length,keys:keys.sort()};
}

export function waitingUnread(rows,stock,reads,uid,today=day()){
  const keys=[];
  for(const row of rows){
    if(row.deleting||
       !['waiting','contacted','visit'].includes(row.status))continue;

    const seen=reads[row.id]||[];
    const alerts=[];

    if(calendarDate(row.expires)&&
       row.expires<=today&&
       !seen.includes('expiry:'+row.expires)){
      alerts.push('expiry:'+row.expires);
    }

    if(row.createdBy!==uid&&!Object.hasOwn(reads,row.id)){
      alerts.push('created');
    }

    for(const u of stock){
      if(!(row.branchIds||[]).includes(u.branchId))continue;
      if(!['volume','price'].every(k=>
        typeof u[k]==='number'&&Number.isFinite(u[k])&&
        (row[k+'Min']==null||u[k]>=row[k+'Min'])&&
        (row[k+'Max']==null||u[k]<=row[k+'Max'])
      ))continue;

      const key=vacancyKey(u);
      if(!seen.includes(key))alerts.push(key);
    }

    if(alerts.length){
      keys.push(JSON.stringify([
        row.id,[...new Set(alerts)].sort()
      ]));
    }
  }
  return {count:keys.length,keys:keys.sort()};
}

export function validSubscription(raw){
  try{
    const url=new URL(raw.endpoint);
    const hosts=[
      'fcm.googleapis.com',
      'android.googleapis.com',
      'web.push.apple.com'
    ];

    if(url.protocol!=='https:'||
       url.username||url.password||url.port||url.hash||
       raw.endpoint.length>4096||
       !(hosts.includes(url.hostname)||
         url.hostname.endsWith('.push.apple.com')||
         url.hostname.endsWith('.push.services.mozilla.com')||
         url.hostname.endsWith('.notify.windows.com'))){
      return false;
    }

    if(typeof raw.keys.p256dh!=='string'||
       raw.keys.p256dh.length>90||
       typeof raw.keys.auth!=='string'||
       raw.keys.auth.length>24)return false;

    ECDH.convertKey(
      Buffer.from(raw.keys.p256dh,'base64url'),
      'prime256v1',undefined,undefined,'uncompressed'
    );

    return /^[A-Za-z0-9_-]+={0,2}$/.test(raw.keys.p256dh)&&
      /^[A-Za-z0-9_-]+={0,2}$/.test(raw.keys.auth)&&
      Buffer.from(raw.keys.p256dh,'base64url').length===65&&
      Buffer.from(raw.keys.auth,'base64url').length===16;
  }catch{
    return false;
  }
}
'''

assets['functions/notification-engine.js'] = r'''
import {FieldValue} from 'firebase-admin/firestore';
import {createHash,randomUUID} from 'node:crypto';
import {
  enabled,globalProfile,workNotificationVisible,
  waitingNotificationVisible,workUnread,waitingUnread
} from './notification-domain.js';

const hash=value=>createHash('sha256').update(value).digest('hex');
const timestamp=()=>FieldValue.serverTimestamp();
const docs=s=>s.docs.map(d=>({id:d.id,...d.data()}));
const chunks=(arr,size)=>Array.from(
  {length:Math.ceil(arr.length/size)},
  (_,i)=>arr.slice(i*size,(i+1)*size)
);

export function createNotificationEngine({db,keys,site,send}){
  let stockCache=null,stockCacheTime=0,stockPromise=null;

  async function stockData(epoch=0){
    if(stockCache&&stockCacheTime>=epoch&&
       Date.now()-stockCacheTime<3000)return stockCache;

    if(stockPromise){
      await stockPromise;
      if(stockCacheTime>=epoch)return stockCache;
    }

    const start=Date.now();
    stockPromise=Promise.all([
      db.collectionGroup('waitingUnits').get(),
      db.collection('workBranches').get(),
      db.collection('branches').get()
    ]).then(([units,directory,branches])=>{
      stockCache={
        units:docs(units),
        archived:docs(directory).filter(b=>b.archived).map(b=>b.id),
        branches:docs(branches)
      };
      stockCacheTime=start;
      return stockCache;
    }).finally(()=>{stockPromise=null;});

    return stockPromise;
  }

  async function loadWork(uid,p){
    const map=new Map();
    const add=s=>docs(s).forEach(d=>map.set(d.id,d));
    const ids=p.branchIds||[];

    if(globalProfile(p)){
      add(await db.collection('workTasks')
        .where('directAssigneeIds','array-contains',uid).get());
    }else{
      await Promise.all([
        db.collection('workTasks')
          .where('createdBy','==',uid).get().then(add),
        ...chunks(ids,30).map(group=>
          db.collection('workTasks')
            .where('branchIds','array-contains-any',group)
            .get().then(add)
        )
      ]);
    }

    const access=docs(
      await db.collection('workTaskAccess')
        .where('uid','==',uid).get()
    ).filter(a=>a.active);

    for(const group of chunks(access,100)){
      const snapshots=await db.getAll(
        ...group.map(a=>db.doc('workTasks/'+a.taskId))
      );

      for(let i=0;i<snapshots.length;i++){
        const s=snapshots[i],a=group[i];
        if(!s.exists)continue;

        const task={id:s.id,...s.data()};
        let assigned=a.primaryThread==='main'&&
          (task.directAssigneeIds||[]).includes(uid);

        if(!assigned&&a.primaryThread&&a.primaryThread!=='main'){
          const child=(await db.doc(
            `workTasks/${s.id}/items/${a.primaryThread}`
          ).get()).data();

          assigned=!!child&&!child.deleted&&
            (child.directAssigneeIds||[]).includes(uid);
        }

        if(assigned&&workNotificationVisible(task,uid,p,assigned)){
          map.set(task.id,task);
        }
      }
    }

    const reads=Object.fromEntries(
      docs(await db.collection('workReads')
        .where('uid','==',uid).get())
        .map(r=>[r.taskId,r])
    );

    return workUnread([...map.values()],reads,uid);
  }

  async function loadWaiting(uid,p,epoch){
    if(p.role!=='manager')return {count:0,keys:[]};

    const map=new Map();
    const add=s=>docs(s).forEach(d=>map.set(d.id,d));

    await Promise.all(
      chunks(p.branchIds||[],30).map(group=>
        db.collection('waitingList')
          .where('branchIds','array-contains-any',group)
          .get().then(add)
      )
    );

    const rows=[...map.values()].filter(
      r=>waitingNotificationVisible(r,uid,p)
    );

    const reads=Object.fromEntries(
      docs(await db.collection(`waitingReads/${uid}/items`).get())
        .map(r=>[r.id,r.seen||[]])
    );

    if(!rows.length)return {count:0,keys:[]};

    const data=await stockData(epoch);
    const blocked=new Set([
      ...data.archived,
      ...data.branches.filter(b=>
        b.importing&&
        (globalProfile(p)||(p.branchIds||[]).includes(b.id))
      ).map(b=>b.id)
    ]);

    return waitingUnread(
      rows,
      data.units.filter(u=>!blocked.has(u.branchId)),
      reads,uid
    );
  }

  async function work(uid){
    const lock=db.doc('pushLocks/'+uid);
    const token=randomUUID();

    const acquired=await db.runTransaction(async tx=>{
      const s=await tx.get(lock);
      if((s.data()?.until||0)>Date.now())return false;
      tx.set(lock,{token,until:Date.now()+150000});
      return true;
    });

    if(!acquired)return;

    try{
      const queue=db.doc('pushQueue/'+uid);
      const queued=await queue.get();
      if(!queued.exists)return;

      const devices=await db.collection('pushDevices')
        .where('uid','==',uid).get();

      if(devices.empty){
        await db.runTransaction(async tx=>{
          const current=await tx.get(queue);
          if(current.data()?.revision===queued.data().revision){
            tx.delete(queue);
          }
        });
        return;
      }

      const [profile,previous]=await Promise.all([
        db.doc('users/'+uid).get(),
        db.doc('pushLedger/'+uid).get()
      ]);

      const p=profile.data(),old=previous.data()||{};
      const active=enabled(p),q=queued.data();

      const [w,v]=active?await Promise.all([
        q.work||!previous.exists
          ? loadWork(uid,p)
          : {count:old.workCount||0,keys:null},
        q.waiting||!previous.exists
          ? loadWaiting(uid,p,q.stockEpoch)
          : {count:old.waitingCount||0,keys:null}
      ]):[{count:0,keys:[]},{count:0,keys:[]}];

      const wf=w.keys
        ? hash(JSON.stringify(w.keys))
        : old.workFingerprint;
      const vf=v.keys
        ? hash(JSON.stringify(v.keys))
        : old.waitingFingerprint;

      const changed=!previous.exists||
        wf!==old.workFingerprint||
        vf!==old.waitingFingerprint||
        active!==old.enabled;

      const version=changed?(old.version||0)+1:old.version;
      const state={
        count:w.count+v.count,
        workCount:w.count,
        waitingCount:v.count,
        version,
        enabled:active
      };

      if(changed){
        const batch=db.batch();
        batch.set(db.doc('pushLedger/'+uid),{
          ...state,
          workFingerprint:wf,
          waitingFingerprint:vf,
          updatedAt:timestamp()
        });
        batch.set(db.doc('pushStatus/'+uid),{
          ...state,updatedAt:timestamp()
        });
        await batch.commit();
      }

      const k=keys(),url=site();

      for(const group of chunks(devices.docs,4)){
        await Promise.all(group.map(async device=>{
          const d=device.data();
          if(d.lastVersion>=version)return;

          try{
            await send(
              d.subscription,
              JSON.stringify({
                uid,
                deviceId:device.id,
                binding:d.binding,
                version,
                count:state.count,
                enabled:active,
                page:state.workCount?'work':'waiting',
                url:url.href
              }),
              {
                vapidDetails:{
                  subject:url.origin,
                  publicKey:k.publicKey,
                  privateKey:k.privateKey
                },
                TTL:86400,
                topic:'storeasy-unread',
                urgency:'normal',
                timeout:5000
              }
            );

            await db.runTransaction(async tx=>{
              const latest=await tx.get(device.ref);
              if(latest.data()?.binding===d.binding){
                if(!active)tx.delete(device.ref);
                else tx.update(device.ref,{lastVersion:version});
              }
            });
          }catch(e){
            if([404,410].includes(e.statusCode)){
              await db.runTransaction(async tx=>{
                const latest=await tx.get(device.ref);
                if(latest.data()?.binding===d.binding){
                  tx.delete(device.ref);
                }
              });
            }else throw e;
          }
        }));
      }

      await db.runTransaction(async tx=>{
        const latest=await tx.get(queue);
        if(latest.data()?.revision===q.revision)tx.delete(queue);
      });
    }finally{
      await db.runTransaction(async tx=>{
        const s=await tx.get(lock);
        if(s.data()?.token===token)tx.delete(lock);
      });
    }
  }

  return {work};
}
'''

assets['functions/index.js'] = r'''
import {createNotificationEngine} from './notification-engine.js';
import {initializeApp} from 'firebase-admin/app';
import {getFirestore,FieldValue} from 'firebase-admin/firestore';
import {onCall,HttpsError} from 'firebase-functions/v2/https';
import {
  onDocumentWritten,onDocumentCreated
} from 'firebase-functions/v2/firestore';
import {onSchedule} from 'firebase-functions/v2/scheduler';
import {setGlobalOptions} from 'firebase-functions/v2';
import {defineSecret,defineString} from 'firebase-functions/params';
import {createHash,randomUUID} from 'node:crypto';
import webpush from 'web-push';
import {
  enabled,workNotificationVisible,
  waitingNotificationVisible,validSubscription
} from './notification-domain.js';

initializeApp();
const db=getFirestore();

setGlobalOptions({
  region:'asia-east1',
  maxInstances:2,
  memory:'256MiB',
  timeoutSeconds:120
});

const vapid=defineSecret('STOREASY_WEB_PUSH_VAPID');
const appURL=defineString('PUSH_APP_URL',{
  default:'https://kai0430xx.github.io/Storeasy_Dashboard/'
});

const hash=value=>createHash('sha256').update(value).digest('hex');
const timestamp=()=>FieldValue.serverTimestamp();
const docs=s=>s.docs.map(d=>({id:d.id,...d.data()}));
const chunks=(arr,size)=>Array.from(
  {length:Math.ceil(arr.length/size)},
  (_,i)=>arr.slice(i*size,(i+1)*size)
);

function site(){
  const u=new URL(appURL.value());
  if(u.protocol!=='https:'||u.search||u.hash){
    throw new Error('PUSH_APP_URL 必須是網站的 HTTPS 根網址');
  }
  if(!u.pathname.endsWith('/'))u.pathname+='/';
  return u;
}

function keys(){
  try{
    const k=JSON.parse(vapid.value());
    if(!k.publicKey||!k.privateKey)throw new Error();
    return k;
  }catch{
    throw new HttpsError(
      'failed-precondition','請先完成背景推播金鑰設定'
    );
  }
}

async function actor(request){
  const uid=request.auth?.uid;
  if(!uid)throw new HttpsError('unauthenticated','請先登入');
  const p=(await db.doc('users/'+uid).get()).data();
  if(!enabled(p)){
    throw new HttpsError('permission-denied','此帳號沒有通知權限');
  }
  return {uid,p};
}

function ownerKey(value){
  if(typeof value!=='string'||!/^\w[\w-]{31,127}$/.test(value)){
    throw new HttpsError('invalid-argument','裝置識別不正確');
  }
  return hash(value);
}

function originCheck(request){
  const origin=request.rawRequest.headers.origin;
  const local=process.env.FUNCTIONS_EMULATOR==='true'&&
    /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin||'');

  if(origin!==site().origin&&!local){
    throw new HttpsError('permission-denied','通知來源網站不符');
  }
}

async function enqueue(
  uid,flags={work:true,waiting:true},stockEpoch=0
){
  await db.runTransaction(async tx=>{
    const ref=db.doc('pushQueue/'+uid);
    const old=await tx.get(ref);
    tx.set(ref,{
      ...Object.fromEntries(
        Object.entries(flags).filter(([,v])=>v)
      ),
      stockEpoch:Math.max(stockEpoch,old.data()?.stockEpoch||0),
      revision:(old.data()?.revision||0)+1,
      enqueuedAt:old.data()?.enqueuedAt||timestamp(),
      touchedAt:timestamp()
    },{merge:true});
  });
}

async function enqueueRegistered(
  uid,flags={work:true,waiting:true}
){
  const devices=await db.collection('pushDevices')
    .where('uid','==',uid).limit(1).get();
  if(!devices.empty)await enqueue(uid,flags);
}

export const pushConfig=onCall({secrets:[vapid]},async request=>{
  await actor(request);
  originCheck(request);
  return {publicKey:keys().publicKey,appUrl:site().href};
});

export const pushSubscribe=onCall({secrets:[vapid]},async request=>{
  const {uid}=await actor(request);
  originCheck(request);

  const {subscription,installationKey}=request.data||{};
  if(!validSubscription(subscription)){
    throw new HttpsError(
      'invalid-argument','推播訂閱不正確或裝置不受支援'
    );
  }

  const ownerHash=ownerKey(installationKey);
  const id=hash(subscription.endpoint),binding=randomUUID();
  const ref=db.doc('pushDevices/'+id);

  await db.runTransaction(async tx=>{
    const [old,devices]=await Promise.all([
      tx.get(ref),
      tx.get(db.collection('pushDevices').where('uid','==',uid))
    ]);

    if(old.exists&&old.data().ownerHash!==ownerHash){
      throw new HttpsError(
        'failed-precondition',
        '裝置識別已變更，請關閉通知後重新啟用'
      );
    }

    if((!old.exists||old.data().uid!==uid)&&devices.size>=10){
      throw new HttpsError(
        'resource-exhausted','每個帳號最多啟用 10 個通知裝置'
      );
    }

    tx.set(ref,{
      uid,ownerHash,binding,
      subscription:{
        endpoint:subscription.endpoint,
        keys:{
          p256dh:subscription.keys.p256dh,
          auth:subscription.keys.auth
        }
      },
      createdAt:old.data()?.createdAt||timestamp(),
      updatedAt:timestamp(),
      lastVersion:0
    });
  });

  await enqueue(uid);
  return {deviceId:id,binding,uid};
});

export const pushUnsubscribe=onCall(async request=>{
  const {uid}=await actor(request);
  originCheck(request);

  const {deviceId,installationKey}=request.data||{};
  if(!/^[a-f0-9]{64}$/.test(deviceId||'')){
    throw new HttpsError('invalid-argument','裝置識別不正確');
  }

  const ownerHash=ownerKey(installationKey);
  const ref=db.doc('pushDevices/'+deviceId);

  await db.runTransaction(async tx=>{
    const s=await tx.get(ref);
    if(!s.exists)return;
    if(s.data().uid!==uid||s.data().ownerHash!==ownerHash){
      throw new HttpsError(
        'permission-denied','無法變更其他裝置'
      );
    }
    tx.delete(ref);
  });

  return {disabled:true};
});

const {work}=createNotificationEngine({
  db,keys,site,send:webpush.sendNotification.bind(webpush)
});

export const pushQueueWorker=onDocumentCreated({
  document:'pushQueue/{uid}',secrets:[vapid],retry:true
},event=>work(event.params.uid));

export const pushQueueSweep=onSchedule({
  schedule:'every 1 minutes',
  secrets:[vapid],
  maxInstances:1,
  timeoutSeconds:540
},async()=>{
  const pending=await db.collection('pushQueue')
    .orderBy('enqueuedAt').limit(30).get();

  for(const group of chunks(pending.docs,4)){
    await Promise.all(group.map(d=>work(d.id)));
  }
});

async function audience(predicate,flags,epoch=0){
  const ids=[...new Set(
    docs(await db.collection('pushDevices').get()).map(d=>d.uid)
  )];

  for(const group of chunks(ids,100)){
    const users=await db.getAll(
      ...group.map(uid=>db.doc('users/'+uid))
    );
    await Promise.all(
      users.filter(s=>predicate(s.id,s.data()))
        .map(s=>enqueue(s.id,flags,epoch))
    );
  }
}

const beforeAfter=e=>[
  e.data?.before.data(),e.data?.after.data()
].filter(Boolean);

export const notifyWork=onDocumentWritten(
  'workTasks/{id}',async e=>{
    const rows=beforeAfter(e);
    const assigned=docs(
      await db.collection('workTaskAccess')
        .where('taskId','==',e.params.id).get()
    ).filter(a=>a.active).map(a=>a.uid);

    await audience(
      (uid,p)=>rows.some(r=>
        workNotificationVisible(r,uid,p,assigned.includes(uid))
      ),
      {work:true}
    );
  }
);

export const notifyWorkAccess=onDocumentWritten(
  'workTaskAccess/{id}',async e=>{
    for(const uid of new Set(beforeAfter(e).map(d=>d.uid))){
      if(uid)await enqueueRegistered(uid,{work:true});
    }
  }
);

export const notifyWorkRead=onDocumentWritten(
  'workReads/{id}',async e=>{
    const uid=e.data?.after.data()?.uid||
      e.data?.before.data()?.uid;
    if(uid)await enqueueRegistered(uid,{work:true});
  }
);

export const notifyWaiting=onDocumentWritten(
  'waitingList/{id}',async e=>{
    const rows=beforeAfter(e);
    await audience(
      (uid,p)=>rows.some(r=>waitingNotificationVisible(r,uid,p)),
      {waiting:true}
    );
  }
);

export const notifyWaitingRead=onDocumentWritten(
  'waitingReads/{uid}/items/{id}',
  e=>enqueueRegistered(e.params.uid,{waiting:true})
);

export const notifyStock=onDocumentWritten(
  'waitingStock/{id}/waitingUnits/{code}',async e=>{
    const branch=(await db.doc('branches/'+e.params.id).get()).data();
    if(branch?.importing)return;
    await audience(
      (uid,p)=>p?.role==='manager',
      {waiting:true},Date.parse(e.time)||Date.now()
    );
  }
);

export const notifyBranch=onDocumentWritten(
  'branches/{id}',async e=>{
    const a=e.data?.before.data(),b=e.data?.after.data();
    if(JSON.stringify([a?.archived,!!a?.importing])!==
       JSON.stringify([b?.archived,!!b?.importing])){
      await audience(
        (uid,p)=>p?.role==='manager',
        {waiting:true},Date.parse(e.time)||Date.now()
      );
    }
  }
);

export const notifyDirectory=onDocumentWritten(
  'workBranches/{id}',async e=>{
    if(e.data?.before.data()?.archived!==
       e.data?.after.data()?.archived){
      await audience(
        (uid,p)=>p?.role==='manager',
        {waiting:true},Date.parse(e.time)||Date.now()
      );
    }
  }
);

export const notifyUser=onDocumentWritten(
  'users/{uid}',async e=>{
    const a=e.data?.before.data(),b=e.data?.after.data();
    if(JSON.stringify([a?.role,a?.branchIds])!==
       JSON.stringify([b?.role,b?.branchIds])){
      await enqueueRegistered(e.params.uid);
    }
  }
);

export const pushExpiryTick=onSchedule({
  schedule:'0 0 * * *',timeZone:'Asia/Taipei'
},()=>audience(
  (uid,p)=>p?.role==='manager',{waiting:true}
));
'''

assets['functions/setup-push.mjs'] = r'''
import webpush from 'web-push';
import {execFileSync,spawnSync} from 'node:child_process';
import {
  mkdtempSync,writeFileSync,readFileSync,existsSync,rmSync
} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';

const project=process.argv[2]||'storeasy-dashboard';
if(!/^[a-z][a-z0-9-]{4,61}[a-z0-9]$/.test(project)){
  throw new Error('專案 ID 不正確');
}

const url=new URL(
  process.argv[3]||
  'https://kai0430xx.github.io/Storeasy_Dashboard/'
);

if(url.protocol!=='https:'||url.search||url.hash){
  throw new Error('請填網站的 HTTPS 根網址');
}
if(!url.pathname.endsWith('/'))url.pathname+='/';

const name='STOREASY_WEB_PUSH_VAPID';
const result=spawnSync('gcloud',[
  'secrets','describe',name,
  '--project',project,'--format=value(name)'
],{encoding:'utf8'});

if(result.status!==0){
  if(!/NOT_FOUND|not found|does not exist/i.test(
    (result.stderr||'')+(result.stdout||'')
  )){
    throw new Error(
      '無法查詢推播金鑰；請先登入 gcloud、選擇正確專案並啟用 Secret Manager API。'
    );
  }

  const folder=mkdtempSync(join(tmpdir(),'storeasy-vapid-'));
  try{
    const file=join(folder,'key.json');
    writeFileSync(file,JSON.stringify(webpush.generateVAPIDKeys()),{
      mode:0o600
    });
    execFileSync('gcloud',[
      'secrets','create',name,
      '--project',project,
      '--replication-policy=automatic',
      '--data-file',file
    ],{stdio:['ignore','ignore','pipe']});
    console.log('推播金鑰已建立。私鑰不會顯示。');
  }finally{
    rmSync(folder,{recursive:true,force:true});
  }
}else{
  console.log('沿用既有推播金鑰，未重新產生。');
}

const file=resolve('functions','.env.'+project);
let text=existsSync(file)?readFileSync(file,'utf8'):'';
const line='PUSH_APP_URL='+JSON.stringify(url.href);
text=/^PUSH_APP_URL=.*$/m.test(text)
  ? text.replace(/^PUSH_APP_URL=.*$/m,line)
  : text+'\n'+line+'\n';

writeFileSync(file,text,{mode:0o600});
console.log('網站網址已設定。接著部署 notifications Cloud Functions。');
'''

assets['src/push-client.ts'] = r'''
import {
  getFunctions,connectFunctionsEmulator,httpsCallable
} from 'firebase/functions';
import {onAuthStateChanged} from 'firebase/auth';
import {auth} from './firebase';

export type PushDevice={
  uid:string;
  deviceId:string;
  binding:string;
};

const functions=getFunctions(undefined,'asia-east1');
if(import.meta.env.VITE_USE_EMULATORS==='true'){
  connectFunctionsEmulator(functions,'127.0.0.1',5001);
}

const base=new URL(import.meta.env.BASE_URL,window.location.href);
const deviceKey='storeasy-push-device:'+base.pathname;
const ownerKey='storeasy-push-owner:'+base.pathname;

export const pushSupported=()=>
  ('Notification'in window)&&
  ('PushManager'in window)&&
  ('serviceWorker'in navigator);

export const iosDevice=()=>
  /iPhone|iPad|iPod/.test(navigator.userAgent)||
  (/Macintosh/.test(navigator.userAgent)&&navigator.maxTouchPoints>1);

export const standalone=()=>
  window.matchMedia('(display-mode: standalone)').matches||
  Boolean((navigator as any).standalone);

export function currentDevice():PushDevice|null{
  try{
    return JSON.parse(localStorage.getItem(deviceKey)||'null');
  }catch{
    return null;
  }
}

function installationKey(){
  let key=localStorage.getItem(ownerKey);
  if(!key){
    key=crypto.randomUUID()+crypto.randomUUID();
    localStorage.setItem(ownerKey,key);
  }
  return key;
}

export async function pushWorker(){
  if(!pushSupported()){
    throw new Error('這個瀏覽器尚不支援背景通知');
  }
  const registration=await navigator.serviceWorker.register(
    new URL('sw.js',base),{scope:base.pathname}
  );
  await navigator.serviceWorker.ready;
  return registration;
}

export async function workerMessage(type:string,value?:unknown){
  const registration=await pushWorker();
  const worker=registration.active;
  if(!worker){
    throw new Error('通知服務尚未準備好，請稍後重試');
  }

  await new Promise<void>((resolve,reject)=>{
    const channel=new MessageChannel();
    const timer=window.setTimeout(
      ()=>reject(new Error('通知服務回應逾時')),10000
    );
    channel.port1.onmessage=e=>{
      clearTimeout(timer);
      channel.port1.close();
      e.data?.ok
        ? resolve()
        : reject(new Error('裝置通知設定失敗'));
    };
    worker.postMessage({type,value},[channel.port2]);
  });
}

const rpc=async(name:string,data:unknown)=>
  ((await httpsCallable(functions,name)(data)).data as any);

export function notificationError(error:any){
  const code=String(error?.code||'');
  if(code.includes('not-found')||
     code.includes('unavailable')||
     code.includes('internal')){
    return '背景通知服務尚未就緒，請確認 Cloud Functions 與最新 Firebase 規則已部署。';
  }
  return error?.message||'通知設定失敗，請稍後重試';
}

export async function enablePush(){
  if(!pushSupported()){
    throw new Error('這個瀏覽器尚不支援背景通知');
  }
  if(iosDevice()&&!standalone()){
    throw new Error(
      'iPhone 請先用 Safari 加入主畫面，再從桌面圖示開啟並啟用通知'
    );
  }

  const uid=auth.currentUser?.uid;
  if(!uid)throw new Error('請先登入');

  const permission=await Notification.requestPermission();
  if(permission!=='granted'){
    throw new Error('尚未允許通知，請在手機或瀏覽器設定開啟');
  }

  const [registration,config]=await Promise.all([
    pushWorker(),rpc('pushConfig',{})
  ]);

  const configured=new URL(config.appUrl);
  if(import.meta.env.VITE_USE_EMULATORS!=='true'&&(
    configured.origin!==base.origin||
    configured.pathname!==base.pathname
  )){
    throw new Error(
      '推播服務的 PUSH_APP_URL 與目前網站不同，請主管確認部署設定'
    );
  }

  const raw=String(config.publicKey).replace(/-/g,'+').replace(/_/g,'/');
  const bytes=Uint8Array.from(
    atob(raw.padEnd(Math.ceil(raw.length/4)*4,'=')),
    c=>c.charCodeAt(0)
  );

  const subscription=
    (await registration.pushManager.getSubscription())||
    await registration.pushManager.subscribe({
      userVisibleOnly:true,
      applicationServerKey:bytes
    });

  const value=await rpc('pushSubscribe',{
    subscription:subscription.toJSON(),
    installationKey:installationKey()
  }) as PushDevice;

  if(auth.currentUser?.uid!==uid){
    await subscription.unsubscribe();
    throw new Error('帳號已變更，請重新啟用通知');
  }

  await workerMessage('bind',value);
  localStorage.setItem(deviceKey,JSON.stringify(value));
  return value;
}

export async function disableLocalPush(){
  localStorage.removeItem(deviceKey);
  if(!('serviceWorker'in navigator))return;

  const registration=await navigator.serviceWorker.getRegistration(
    base.href
  );
  if(!registration)return;

  try{await workerMessage('unbind');}catch{}
  try{
    await (await registration.pushManager.getSubscription())?.unsubscribe();
  }catch{}
  try{await (navigator as any).clearAppBadge?.();}catch{}
}

export async function disablePush(){
  const device=currentDevice(),uid=auth.currentUser?.uid;
  await disableLocalPush();

  if(device&&uid===device.uid){
    await Promise.race([
      rpc('pushUnsubscribe',{
        deviceId:device.deviceId,
        installationKey:installationKey()
      }),
      new Promise((_,reject)=>setTimeout(
        ()=>reject(new Error(
          '裝置已停用；伺服器連線逾時，失效訂閱將在後續推播自動清除'
        )),5000
      ))
    ]);
  }
}

export async function logoutNotifications(){
  try{await disablePush();}catch{}
}

onAuthStateChanged(auth,user=>{
  const device=currentDevice();
  if(device&&device.uid!==user?.uid){
    void disableLocalPush().catch(()=>{});
  }
});
'''

assets['src/NotificationCenter.tsx'] = r'''
import {useEffect,useState} from 'react';
import {doc,onSnapshot} from 'firebase/firestore';
import {Bell,X} from 'lucide-react';
import {db} from './firebase';
import {
  currentDevice,disablePush,enablePush,iosDevice,
  notificationError,pushSupported,standalone,workerMessage,
  PushDevice
} from './push-client';
import './notifications.css';

export default function NotificationCenter({
  uid,role
}:{uid:string;role:string}){
  const [open,setOpen]=useState(false);
  const [device,setDevice]=useState<PushDevice|null>(currentDevice);
  const [active,setActive]=useState(false);
  const [count,setCount]=useState<number|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const supported=pushSupported();
  const needsInstall=iosDevice()&&!standalone();

  useEffect(()=>{
    setActive(false);
    setCount(null);
    if(!device||device.uid!==uid)return;

    return onSnapshot(doc(db,'pushDevices',device.deviceId),s=>{
      setActive(
        s.exists()&&s.data().uid===uid&&
        s.data().binding===device.binding&&
        pushSupported()&&Notification.permission==='granted'
      );
    },()=>setActive(false));
  },[uid,device?.deviceId,device?.binding]);

  useEffect(()=>{
    setCount(null);
    if(!active||!device)return;

    return onSnapshot(doc(db,'pushStatus',uid),s=>{
      const value=s.data();
      if(!value)return;
      setCount(value.count);
      void workerMessage('badge',{
        ...device,version:value.version,count:value.count
      }).catch(()=>{});
    });
  },[uid,active,device?.binding]);

  async function enable(){
    if(busy)return;
    setBusy(true);setError('');setNotice('');
    try{
      const value=await enablePush();
      setDevice(value);
      setNotice('此裝置已啟用背景通知');
    }catch(e){
      setError(notificationError(e));
    }finally{
      setBusy(false);
    }
  }

  async function disable(){
    if(busy)return;
    setBusy(true);setError('');setNotice('');
    try{
      await disablePush();
      setNotice('此裝置通知已停用');
    }catch(e){
      setError(notificationError(e));
    }finally{
      setDevice(null);setActive(false);setCount(null);setBusy(false);
    }
  }

  return <>
    <button type="button" className="notification-settings-button"
      title="通知設定" aria-label="通知設定"
      onClick={()=>{
        setOpen(true);setError('');setNotice('');
      }}>
      <Bell size={18}/>
      {active&&count!==null&&count>0&&
        <span>{count>99?'99+':count}</span>}
    </button>

    {open&&<div className="modal-backdrop">
      <section className="modal notification-modal"
        role="dialog" aria-modal="true" aria-label="通知設定">
        <div className="modal-heading">
          <h2>通知設定</h2>
          <button type="button" aria-label="關閉"
            disabled={busy} onClick={()=>setOpen(false)}>
            <X size={20}/>
          </button>
        </div>

        <p>
          沒開網頁時，也能收到
          {role==='manager'?'待辦與所屬據點候補':'待辦'}提醒。
          桌面圖示數字依系統支援顯示，每筆只算一次。
        </p>
        <p className="hint">
          {role==='manager'
            ? '候補據點包含所屬分店才會提醒；待辦依可查看事項的未讀紅點。'
            : '只有明確指派給你的主事項或子項目會通知；能查看全部事項不代表會收到全部通知。'}
        </p>

        <p className="notification-state">
          此裝置：<strong>{active?'已啟用':'尚未啟用'}</strong>
          {active&&count!==null&&<span> · 未讀 {count} 筆</span>}
        </p>

        {needsInstall&&<div className="alert">
          iPhone 請先用 Safari 開啟網站，按分享 → 加入主畫面，
          再從桌面圖示開啟本網站並啟用通知。需 iOS 16.4 以上。
        </div>}

        {!supported&&!needsInstall&&<div className="alert">
          目前瀏覽器不支援背景通知，
          請改用支援的瀏覽器或加入主畫面後再試。
        </div>}

        {supported&&Notification.permission==='denied'&&
          <p className="hint">
            通知權限已關閉，請到手機或瀏覽器的通知設定重新允許。
          </p>}

        <p className="hint">
          通知只顯示未讀筆數，不放客人個資或訊息內容。
          系統可能因專注模式、網路或省電設定延遲；
          此設定只影響這個裝置。
        </p>

        {error&&<p role="alert" className="alert error">{error}</p>}
        {notice&&<p role="status" className="alert success">{notice}</p>}

        <div className="notification-actions">
          <button type="button" className="primary"
            disabled={busy||!supported||needsInstall}
            onClick={enable}>
            {busy?'處理中…':active
              ? '重新連線通知':'開啟此裝置通知'}
          </button>
          <button type="button" className="secondary"
            disabled={busy||!device||device.uid!==uid}
            onClick={disable}>
            停用此裝置通知
          </button>
        </div>
      </section>
    </div>}
  </>;
}
'''

assets['src/notifications.css'] = r'''
.notification-settings-button {
  position:relative;
  display:inline-flex;
  align-items:center;
  padding:5px;
}
.notification-settings-button > span {
  position:absolute;
  top:-6px;
  right:-7px;
  min-width:16px;
  padding:1px 4px;
  border-radius:10px;
  background:#d42036;
  color:white;
  font-size:10px;
  line-height:14px;
}
.notification-modal p { line-height:1.7; }
.notification-state {
  padding:12px;
  background:#f3f6fb;
  border-radius:8px;
}
.notification-actions {
  display:flex;
  flex-wrap:wrap;
  gap:12px;
  margin-top:20px;
}
'''

assets['public/sw.js'] = r'''
/* No page caching: normal website updates remain fresh. */
const stateCache='storeasy-push-state:'+self.registration.scope;
const stateURL=new URL('__push_state__',self.registration.scope).href;
const tag='storeasy-unread:'+new URL(self.registration.scope).pathname;
let chain=Promise.resolve();

async function readState(){
  const response=await(await caches.open(stateCache)).match(stateURL);
  return response?response.json():null;
}

async function writeState(value){
  await(await caches.open(stateCache)).put(
    stateURL,
    new Response(JSON.stringify(value),{
      headers:{'Content-Type':'application/json'}
    })
  );
}

async function badge(count){
  try{
    if(count>0&&self.navigator.setAppBadge){
      await self.navigator.setAppBadge(count);
    }else if(self.navigator.clearAppBadge){
      await self.navigator.clearAppBadge();
    }
  }catch{}
}

function serial(fn){
  chain=chain.catch(()=>{}).then(fn);
  return chain;
}

self.addEventListener('install',event=>
  event.waitUntil(self.skipWaiting())
);
self.addEventListener('activate',event=>
  event.waitUntil(self.clients.claim())
);

self.addEventListener('message',event=>{
  const source=event.source?.url;
  if(!source||!source.startsWith(self.registration.scope))return;

  event.waitUntil(serial(async()=>{
    const data=event.data||{},old=await readState();

    if(data.type==='bind'){
      const v=data.value;
      if(!v||typeof v.uid!=='string'||
         typeof v.deviceId!=='string'||
         typeof v.binding!=='string'){
        throw new Error('Invalid device binding');
      }
      await writeState({...v,enabled:true,version:0,count:0});
      await badge(0);
    }else if(data.type==='unbind'){
      await writeState({enabled:false});
      await badge(0);
      for(const notification of
          await self.registration.getNotifications({tag})){
        notification.close();
      }
    }else if(data.type==='badge'){
      const v=data.value;
      if(old?.enabled&&v?.uid===old.uid&&
         v?.deviceId===old.deviceId&&v?.binding===old.binding&&
         Number.isInteger(v.count)&&v.count>=0&&
         v.version>=old.version){
        await writeState({...old,version:v.version,count:v.count});
        await badge(v.count);
      }
    }

    event.ports?.[0]?.postMessage({ok:true});
  }).catch(()=>event.ports?.[0]?.postMessage({ok:false})));
});

self.addEventListener('push',event=>
  event.waitUntil(serial(async()=>{
    let incoming;
    try{incoming=event.data?.json();}catch{return;}

    const old=await readState();
    if(!old?.enabled||!incoming||
       incoming.uid!==old.uid||
       incoming.deviceId!==old.deviceId||
       incoming.binding!==old.binding||
       !Number.isInteger(incoming.count)||incoming.count<0||
       !Number.isInteger(incoming.version))return;

    const value=incoming.version>=old.version
      ? {...old,...incoming}
      : old;

    await writeState(value);
    await badge(value.count);

    const target=new URL(self.registration.scope);
    target.hash=value.count
      ? (value.page==='waiting'?'waiting':'work')
      : 'dashboard';

    await self.registration.showNotification(
      value.count?'收多易・未讀提醒':'收多易・提醒已更新',
      {
        body:value.count
          ? '你有 '+value.count+' 筆未讀提醒。'
          : '目前沒有未讀提醒。',
        tag,
        renotify:false,
        silent:incoming.version<=old.version||
          value.count<old.count||value.count===0,
        icon:new URL(
          'icons/app-192.png',self.registration.scope
        ).href,
        data:{
          url:target.href,
          uid:value.uid,
          binding:value.binding
        }
      }
    );
  }))
);

self.addEventListener('notificationclick',event=>{
  event.notification.close();
  event.waitUntil(serial(async()=>{
    const state=await readState();
    const data=event.notification.data||{};

    if(!state?.enabled||state.uid!==data.uid||
       state.binding!==data.binding)return;

    const target=new URL(data.url||self.registration.scope);
    if(target.origin!==new URL(self.registration.scope).origin||
       !target.href.startsWith(self.registration.scope))return;

    const windows=await self.clients.matchAll({
      type:'window',includeUncontrolled:true
    });
    const existing=windows.find(client=>
      client.url.startsWith(self.registration.scope)
    );

    if(existing){
      await existing.navigate(target.href);
      await existing.focus();
    }else{
      await self.clients.openWindow(target.href);
    }
  }));
});

self.addEventListener('pushsubscriptionchange',event=>
  event.waitUntil(serial(async()=>{
    const state=await readState();
    if(!state?.enabled)return;
    await self.registration.showNotification(
      '收多易・通知連線已變更',
      {
        body:'請開啟網頁的通知設定，重新啟用此裝置通知。',
        tag,
        icon:new URL(
          'icons/app-192.png',self.registration.scope
        ).href,
        data:{
          url:self.registration.scope,
          uid:state.uid,
          binding:state.binding
        }
      }
    );
  }))
);
'''

assets['public/manifest.webmanifest'] = r'''
{
  "id":"./",
  "name":"收多易營運管理平台",
  "short_name":"收多易",
  "lang":"zh-Hant",
  "start_url":"./",
  "scope":"./",
  "display":"standalone",
  "background_color":"#f5f7fb",
  "theme_color":"#123d73",
  "icons":[
    {
      "src":"icons/app-192.png",
      "sizes":"192x192",
      "type":"image/png",
      "purpose":"any maskable"
    },
    {
      "src":"icons/app-512.png",
      "sizes":"512x512",
      "type":"image/png",
      "purpose":"any maskable"
    }
  ]
}
'''

assets['PUSH_SETUP.md'] = r'''
# 背景通知部署

GitHub Pages 只發布前端。關閉網站後更新通知與圖示數字，
還必須部署 notifications Cloud Functions。
需要 Blaze 與具有部署、Secret Manager 權限的專案帳號。
Cloud Functions、Firestore、Cloud Scheduler 與 Secret Manager 依用量計費。

店長收到所屬據點候補黃點、需求到期紅點及可查看待辦紅點。
主管、管理員只收明確指派自己的主事項或子項目所屬待辦。
同帳號電腦讀取一筆，背景服務傳送剩餘絕對數量到所有啟用裝置：
4→3，讀完→0。每筆事項或候補只計一次。

## 首次部署

先完成 GitHub 更新及 Actions，再於 Google Cloud Shell 執行：

    gcloud config set project storeasy-dashboard
    gcloud services enable secretmanager.googleapis.com
    git clone https://github.com/Kai0430xx/Storeasy_Dashboard.git storeasy-push
    cd storeasy-push
    npm ci
    npm --prefix functions ci --ignore-scripts
    node functions/setup-push.mjs storeasy-dashboard https://kai0430xx.github.io/Storeasy_Dashboard/
    npx firebase login --no-localhost
    npx firebase deploy --only functions:notifications,firestore:rules --project storeasy-dashboard

資料夾已存在時進入既有儲存庫並 git pull --ff-only，不重複 clone。
setup-push.mjs 沿用既有金鑰，不要刪除或重新產生金鑰。
私鑰只存 Secret Manager，不貼入網頁或 GitHub。
functions/.secret.local 及 functions/.env.* 不可加入 Git。

第一次部署可能要求啟用相關 API 與建立 Google 服務身分。
Eventarc service agent 尚未就緒時，等建立完成再重試同一部署指令。
權限被拒請由專案管理者處理 IAM，不放寬 Firestore 規則。

## 啟用與驗證

1. iPhone 使用 iOS 16.4+ Safari → 分享 → 加入主畫面。
2. 從桌面圖示登入，點頂端鈴鐺「通知設定」。
3. 點「開啟此裝置通知」並允許系統通知；每台裝置各自啟用。
4. 手機關閉網站，由另一帳號建立符合通知範圍的提醒。
5. 同帳號電腦讀完一筆，手機應由 4→3，全部讀完清除數字。
6. 驗證未指派主管的待辦不通知主管，候補到期通知店長。
7. 登出會清除本機圖示數字與訂閱，不沿用到其他帳號。

推播不含姓名、電話、對話或備註。
背景 Web Push 需顯示系統通知，不能保證完全靜默只改數字。
數字下降採靜音通知。圖示數字依作業系統、瀏覽器與桌面支援。
網路、專注模式、省電及系統排程可能造成延遲。

後續修改 Functions 仍須重新 deploy；只更新 Pages 不會更新背景服務。
佇列即時處理，未完成工作由每分鐘排程補處理，
候補到期於台灣時間午夜重新計算。
'''

manual_addition = r'''
// background-push-manual-v1
manualPages.push({
 id:'notifications',
 title:'通知與加入主畫面',
 intro:'啟用背景推播，關閉網頁後接收未讀提醒及支援裝置的圖示數字。',
 access:'店長／主管／管理員；每個帳號及裝置獨立設定',
 topics:[
  {
   title:'iPhone 加入主畫面與啟用通知',
   steps:[
    '使用 iOS 16.4 以上的 Safari 開啟網站，按分享 → 加入主畫面。',
    '從桌面圖示開啟網站並登入，點頂端鈴鐺「通知設定」。',
    '點「開啟此裝置通知」，在系統詢問時允許通知；每台手機或電腦都要各自啟用。'
   ],
   result:'背景服務部署完成後，沒有開啟網頁也可收到簡短系統通知；支援的系統會更新圖示數字。Android 的圖示數字依瀏覽器與桌面啟動器支援，未必顯示數字。'
  },
  {
   title:'未讀數量與清除提醒',
   steps:[
    '店長數字合計可查看的未讀待辦，加上候補據點包含自己所屬分店的候補提醒；只因自己建立、但未選所屬店的候補不計入。主管與管理員只接收明確指派給自己的主事項或子項目所屬待辦，不計候補；只有查看權限但未被指派時不會收到通知。每份主事項或每筆候補只計一次；同筆候補同時有紅點與黃點也只算一筆。',
    '點開對應待辦或候補明細標記已讀；子項目需點開該子項目。背景服務重新計算後同步到同帳號所有已啟用的裝置；例如原本 4 筆，在電腦讀完 1 筆，未開網頁的手機也會更新為 3，全部讀完清除數字。',
    '通知只顯示未讀筆數，點通知可開啟待辦或候補頁；點通知本身不會自動把所有資料設為已讀。'
   ],
   result:'系統通知不含客人姓名、電話、備註或對話內容。到期候補自台灣日期到期當天提醒；已承租、已取消停止提醒。'
  },
  {
   title:'停用通知與裝置限制',
   steps:[
    '在鈴鐺「通知設定」按「停用此裝置通知」；登出也會取消本機訂閱及清除本機圖示數字。',
    '通知權限被拒絕時，請到手機或瀏覽器的通知設定重新允許，再開啟網站通知。',
    '若通知連線失效，重新開啟通知設定並點「重新連線通知」；每個帳號最多啟用 10 個裝置。'
   ],
   result:'背景更新會伴隨簡短系統通知，不能保證只更新數字而完全不顯示通知。網路、專注模式、省電與系統限制可能延遲，圖示數字不是即時到達保證。'
  },
  {
   title:'主管部署背景通知服務',
   steps:[
    '僅更新 GitHub Pages 不會啟用背景推播，還需部署 notifications Cloud Functions 與最新 Firestore 規則。',
    '由專案管理者依 PUSH_SETUP.md 完成 Secret Manager 金鑰與網站網址設定；私鑰不貼到網頁或 GitHub。',
    '首次部署後，使用實際手機加入主畫面、允許通知、關閉網站，再由另一帳號建立提醒驗證。'
   ],
   result:'服務尚未部署時，通知設定會提示背景服務尚未就緒；既有網頁內紅點、黃點繼續運作。'
  }
 ]
});
'''

rules_addition = r'''
// background-push-v1: device registration is callable-only.
match /pushDevices/{deviceId} {
  allow get: if workUser() && resource.data.uid==request.auth.uid;
  allow list,create,update,delete: if false;
}
match /pushStatus/{uid} {
  allow get: if signedIn() && request.auth.uid==uid;
  allow list,create,update,delete: if false;
}
'''

changes = {name:text.encode('utf-8') for name,text in assets.items()}

def png_icon(size):
    rows=[]
    for y in range(size):
        row=bytearray()
        for x in range(size):
            a,b=x/size,y/size
            color=(18,61,115)
            if .17<a<.83 and .17<b<.83:
                color=(255,211,51)
            if .31<a<.69 and .34<b<.70:
                color=(18,61,115)
            if .29<a<.71 and .31<b<.36:
                color=(18,61,115)
            if .35<a<.65 and any(
                abs(b-h)<.012 for h in [.44,.52,.60]
            ):
                color=(255,255,255)
            row.extend(color)
        rows.append(b'\x00'+row)

    def chunk(kind,data):
        return (
            struct.pack('!I',len(data))+kind+data+
            struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
        )

    return (
        b'\x89PNG\r\n\x1a\n'+
        chunk(b'IHDR',struct.pack('!2I5B',size,size,8,2,0,0,0))+
        chunk(b'IDAT',zlib.compress(b''.join(rows),9))+
        chunk(b'IEND',b'')
    )

for size in [192,512]:
    changes['public/icons/app-'+str(size)+'.png']=png_icon(size)

def read(name):
    return (root/name).read_text(encoding='utf-8')

def put(name,text):
    changes[name]=text.encode('utf-8')

def replace_once(text,pattern,new,label):
    result,n=re.subn(pattern,lambda m:new,text,count=1)
    if n!=1:
        raise SystemExit('停止：找不到 '+label+'，尚未寫入更新。')
    return result

main=read('src/main.tsx')

if 'import NotificationCenter ' not in main:
    main=(
        'import NotificationCenter from "./NotificationCenter";\n'
        'import {logoutNotifications} from "./push-client";\n'
        +main
    )

if '<NotificationCenter ' not in main:
    main=replace_once(
        main,
        r'<span\s+className="live-dot"\s*/>',
        '{canWrite&&profile&&'
        '<NotificationCenter uid={user.uid} role={profile.role}/>}\n'
        '<span className="live-dot" />',
        '頂端即時同步區'
    )

if 'logoutNotifications().finally' not in main:
    main=replace_once(
        main,
        r'onClick=\{\(\)\s*=>\s*signOut\(auth\)\}',
        'onClick={() => {'
        'void logoutNotifications().finally(()=>signOut(auth));}}',
        '登出按鈕'
    )

put('src/main.tsx',main)

manual=read('src/manual-content.ts')
if '// background-push-manual-v1' in manual:
    manual=manual.split('// background-push-manual-v1')[0]
put('src/manual-content.ts',manual.rstrip()+'\n'+manual_addition)

rules=read('firestore.rules')
if '// background-push-v1' not in rules:
    rules=replace_once(
        rules,
        r'match\s+/users/\{uid\}\s*\{',
        rules_addition+'\nmatch /users/{uid} {',
        'Firestore users 規則'
    )
put('firestore.rules',rules)

html=read('index.html')
if 'manifest.webmanifest' not in html:
    html=replace_once(
        html,
        r'</head>',
        '<link rel="manifest" href="./manifest.webmanifest"/>'
        '<link rel="apple-touch-icon" href="./icons/app-192.png"/>'
        '<meta name="apple-mobile-web-app-capable" content="yes"/>'
        '<meta name="apple-mobile-web-app-title" content="收多易"/>'
        '</head>',
        'HTML head'
    )
put('index.html',html)

config=json.loads(read('firebase.json'))
functions=config.get('functions',[])
if isinstance(functions,dict):
    functions=[functions]

functions=[
    f for f in functions if f.get('codebase')!='notifications'
]
if any(f.get('source')=='functions' for f in functions):
    raise SystemExit('停止：functions 已有其它用途，尚未寫入。')

functions.append({
    'source':'functions',
    'codebase':'notifications',
    'ignore':['node_modules','.secret.local','*.log','test/**'],
    'predeploy':['npm --prefix "$RESOURCE_DIR" ci --ignore-scripts']
})
config['functions']=functions
config.setdefault('emulators',{})['functions']={'port':5001}
put('firebase.json',json.dumps(config,ensure_ascii=False,indent=2)+'\n')

ignore=read('.gitignore') if (root/'.gitignore').exists() else ''
for line in [
    'functions/node_modules/',
    'functions/.secret.local',
    'functions/.env*'
]:
    if line not in ignore.splitlines():
        ignore+='\n'+line+'\n'
put('.gitignore',ignore)

workflow='.github/workflows/update-lease-features.yml'
yaml=read(workflow)
if 'PUSH_SETUP.md' not in yaml:
    anchor=re.search(r'(?m)^(\s*)git add src',yaml)
    if not anchor:
        raise SystemExit('停止：找不到 Actions git add，尚未寫入。')
    yaml=replace_once(
        yaml,
        r'(?m)^(\s*)git add src[^\n]*',
        anchor.group(1)+
        'git add src public functions firebase.json index.html '
        'firestore.rules .gitignore PUSH_SETUP.md',
        'Actions git add'
    )
put(workflow,yaml)

backup=root/'.update-backups'/(
    'background-push-'+
    datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
)

for name,data in changes.items():
    target=root/name
    if target.exists() and target.read_bytes()==data:
        continue
    if target.exists():
        saved=backup/name
        saved.parent.mkdir(parents=True,exist_ok=True)
        saved.write_bytes(target.read_bytes())
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(data)

subprocess.run([
    'npm','install','--prefix','functions',
    '--package-lock-only','--ignore-scripts',
    '--cache',str(Path(tempfile.gettempdir())/'storeasy-npm-cache')
],cwd=root,check=True)

print(
    '背景通知程式與手冊已更新。'
    '正式啟用仍須依 PUSH_SETUP.md 部署 Firebase。'
)
