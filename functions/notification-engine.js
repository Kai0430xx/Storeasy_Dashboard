
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
