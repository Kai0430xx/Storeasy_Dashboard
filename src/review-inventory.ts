import {
 collection,doc,getDoc,getDocs,query,where,documentId,
 runTransaction,serverTimestamp,deleteField
} from 'firebase/firestore';
import {auth,db} from './firebase';
import {normalizeUnits,validDate,taipeiDate,inventoryStats} from './domain.js';
import {inventorySignature,validateInventoryChange} from './inventory-diff.js';
import {pricingUpdate,priceSnapshot} from './pricing.js';
import {vacancyDate} from './targets.js';
import {sourceFiles} from './import-actions';

const time=()=>serverTimestamp();

export async function reviewInventory(data:any){
 const uid=auth.currentUser?.uid;
 if(!uid)throw new Error('請先登入');
 if(typeof data.branchId!=='string'||!data.branchId||data.branchId.includes('/'))
  throw new Error('據點不合法');
 if(!/^[a-zA-Z0-9-]{8,80}$/.test(data.reviewId))
  throw new Error('請重新分析匯入檔案');
 if(!validDate(data.effectiveDate)||data.effectiveDate>taipeiDate())
  throw new Error('盤點日期不合法');
 const files=sourceFiles(data,'inventory');
 if(!Array.isArray(data.changes)||data.changes.length>10000)
  throw new Error('差異資料不合法');
 if(!data.changes.length)return {};

 const normalized=normalizeUnits(data.changes.map((c:any)=>c.after));
 const jobs=data.changes.map((c:any,i:number)=>({
  ...c,after:normalized[i],
  exitReason:String(c.exitReason||'').trim(),
  date:c.date||data.effectiveDate
 }));
 for(const job of jobs){
  if(!validDate(job.date)||job.date>taipeiDate())
   throw new Error(job.after.code+'：異動日期不合法');
  validateInventoryChange(job.before,job.after,job,taipeiDate());
 }

 const branch=doc(db,'branches',data.branchId),token=data.reviewId;
 if((await getDoc(doc(branch,'imports',token))).exists())return {};
 let locked=false,completed=0;

 try{
  await runTransaction(db,async tx=>{
   const s=await tx.get(branch);
   if(!s.exists())throw new Error('據點不存在');
   const b=s.data();
   if(b.importing&&Date.now()-b.importing.startedAt<600000)
    throw new Error('據點有其它匯入正在執行，請稍後再試');
   if(b.inventoryDate&&data.effectiveDate<b.inventoryDate)
    throw new Error('盤點日期不得早於上次盤點');
   tx.update(branch,{
    importing:{operation:'reviewInventory',token,by:uid,startedAt:Date.now()},
    revision:b.revision+1
   });
  });
  locked=true;

  const current=new Map<string,any>();
  for(let i=0;i<jobs.length;i+=30){
   const s=await getDocs(query(
    collection(branch,'units'),
    where(documentId(),'in',jobs.slice(i,i+30).map((j:any)=>j.after.code))
   ));
   for(const d of s.docs)current.set(d.id,d.data());
  }

  const jobKey=(job:any)=>JSON.stringify([
   job.after,job.type,job.month,job.date,
   job.exitCategory||'',job.exitReason,data.effectiveDate
  ]);
  const done=(old:any,job:any)=>
   old?.reviewImport?.id===token
   &&old.reviewImport.key===jobKey(job)
   &&inventorySignature(old)===old.reviewImport.after;

  for(const job of jobs){
   const old=current.get(job.after.code);
   if(old?.reviewImport?.id===token){
    if(!done(old,job))
     throw new Error(job.after.code+'：上次已匯入，內容已改變，請重新分析');
   }else if(inventorySignature(old)!==job.signature){
    throw new Error(job.after.code+'：分析後倉位已被修改，請重新分析');
   }
   if(!done(old,job)){
    validateInventoryChange(old,job.after,job,taipeiDate());
    if(old?.lastEventDate&&job.date<old.lastEventDate)
     throw new Error(job.after.code+'：日期不得早於上一筆異動');
    const pricing=pricingUpdate(old,job.after,data.effectiveDate,null);
    if(job.type!=='sync')priceSnapshot({...job.after,...pricing},job.date);
   }
  }

  for(const job of jobs){
   const unit=doc(branch,'units',job.after.code);
   const month=doc(branch,'months',job.month);
   const nowMonth=doc(branch,'months',taipeiDate().slice(0,7));
   const event=doc(branch,'events','review_'+token+'_'+encodeURIComponent(job.after.code));

   await runTransaction(db,async tx=>{
    const [bs,us,ms,ns]=await Promise.all([
     tx.get(branch),tx.get(unit),tx.get(month),tx.get(nowMonth)
    ]);
    const b=bs.data(),old=us.data();
    if(!b||b.importing?.token!==token||b.importing.by!==uid)
     throw new Error('匯入鎖定已變更');
    if(done(old,job))return;
    if(inventorySignature(old)!==job.signature)
     throw new Error(job.after.code+'：倉位已被修改，請重新分析');
    validateInventoryChange(old,job.after,job,taipeiDate());

    const status=job.after.leasePeriod?'rented':'vacant';
    const record=job.type!=='sync';
    const next:any={
     ...old,...job.after,
     ...pricingUpdate(old,job.after,data.effectiveDate,null),
     status,missing:false,archived:false,
     vacantSince:vacancyDate(old,status,job.date),
     updatedAt:time()
    };
    if(record){
     next.lastEventDate=job.date;
     next.lastEventId=event.id;
    }else{
     next.lastEventId=old?.lastEventId||null;
     next.lastEventDate=old?.lastEventDate||null;
    }

    const beforeStats=old&&!old.missing&&!old.archived
     ?inventoryStats([old]):{total:0,rented:0,vacant:0};
    const total=b.total+1-beforeStats.total;
    const rented=b.rented+(status==='rented'?1:0)-beforeStats.rented;
    const vacant=b.vacant+(status==='vacant'?1:0)-beforeStats.vacant;
    if(Math.min(total,rented,vacant)<0||total!==rented+vacant)
     throw new Error('據點統計不一致，請先核對倉位資料');

    next.reviewImport={id:token,key:jobKey(job),after:inventorySignature(next)};
    tx.set(unit,next);

    if(record){
     const price=priceSnapshot(next,job.date);
     tx.set(event,{
      code:job.after.code,type:job.type,date:job.date,month:job.month,
      activities:[],
      exitCategory:job.type==='exit'?job.exitCategory:'',
      exitReason:job.type==='exit'?job.exitReason:'',
      priceSnapshot:price,
      unitSnapshot:{
       dimensions:next.dimensions,volume:next.volume,
       price:price.price,note:next.note,
       leasePeriod:next.leasePeriod,leaseStart:next.leaseStart,
       leaseEnd:next.leaseEnd
      },
      previousLease:{
       leasePeriod:old?.leasePeriod||'',
       leaseStart:old?.leaseStart||null,
       leaseEnd:old?.leaseEnd||null,
       vacantSince:old?.vacantSince||null
      },
      previousEventId:old?.lastEventId||null,
      previousEventDate:old?.lastEventDate||null,
      createdBy:uid,createdAt:time(),voided:false,
      importRun:token,importSource:files.total,
      kpiCounted:ms.data()?.source!=='import',
      ...(['transferIn','transferOut'].includes(job.type)?{
       transferMode:'external',transferGroup:event.id,
       peerCode:'',peerEventId:''
      }:{})
     });
     if(ms.data()?.source!=='import'){
      tx.set(month,{
       source:'live',
       [job.type]:(ms.data()?.[job.type]||0)+1,
       updatedAt:time()
      },{merge:true});
     }
    }
    if(ns.data()?.source!=='import'){
     tx.set(nowMonth,{
      source:'live',total,rented,vacant,
      snapshotDate:taipeiDate(),updatedAt:time()
     },{merge:true});
    }
    tx.update(branch,{
     total,rented,vacant,revision:b.revision+1,
     importing:{...b.importing,startedAt:Date.now()},
     updatedAt:time()
    });
   });
   completed++;
  }

  await runTransaction(db,async tx=>{
   const bs=await tx.get(branch),b=bs.data();
   if(!b||b.importing?.token!==token)throw new Error('匯入鎖定已變更');
   tx.update(branch,{
    inventoryDate:data.effectiveDate,
    inventorySource:{...files,id:token,mode:'differences'},
    importing:deleteField(),revision:b.revision+1,updatedAt:time()
   });
   tx.set(doc(branch,'imports',token),{
    total:b.total,rented:b.rented,vacant:b.vacant,
    files,effectiveDate:data.effectiveDate,mode:'differences',
    changedCodes:jobs.map((j:any)=>j.after.code),
    by:uid,createdAt:time()
   });
  });
  locked=false;
  return {};
 }catch(e:any){
  throw new Error(`已完成 ${completed} 筆差異，其餘尚未完成：${e.message}。可重試相同內容，或重新分析；已完成的異動不會重複加計。`);
 }finally{
  if(locked){
   await runTransaction(db,async tx=>{
    const s=await tx.get(branch);
    if(s.data()?.importing?.token===token)
     tx.update(branch,{importing:deleteField()});
   }).catch(()=>{});
  }
 }
}

// storeasy-inventory-review-v1
