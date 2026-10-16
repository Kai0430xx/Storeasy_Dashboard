
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
