import {collection,doc,getDoc,runTransaction,serverTimestamp} from 'firebase/firestore';
import {auth,db} from './firebase';
import {parseLease} from './lease.js';
import {validDate,taipeiDate} from './domain.js';
import {priceSnapshot} from './pricing.js';

const time=()=>serverTimestamp();
const key=(v:any)=>{
 if(typeof v!=='string'||!v||v.includes('/'))throw new Error('據點或倉位編號不合法');
 return v;
};
const previous=(u:any)=>({
 leasePeriod:u.leasePeriod||'',
 leaseStart:u.leaseStart||null,
 leaseEnd:u.leaseEnd||null,
 vacantSince:u.vacantSince||null
});

export async function recordTransfer(data:any){
 const branchId=key(data.branchId),code=key(data.code),date=data.date,uid=auth.currentUser?.uid;
 if(!uid)throw new Error('請先登入');
 if(!['transferOut','transferIn'].includes(data.type)||!validDate(date)||date>taipeiDate())throw new Error('轉倉日期或類型不合法');
 const local=data.type==='transferOut'&&data.mode==='local';
 if(data.type==='transferOut'&&!['local','external'].includes(data.mode))throw new Error('請選擇轉出方式');
 const target=local?key(data.targetCode):null;
 if(target===code)throw new Error('不能轉到原倉位');
 const lease=data.type==='transferIn'||local?parseLease(data.leasePeriod):null;
 if(lease&&!lease.leasePeriod)throw new Error('請填寫新租期');

 const branch=doc(db,'branches',branchId);
 const month=doc(branch,'months',date.slice(0,7));
 const nowMonth=doc(branch,'months',taipeiDate().slice(0,7));
 const refs=[doc(branch,'units',code),...(local?[doc(branch,'units',target!)]:[])];
 const eventRefs=refs.map(()=>doc(collection(branch,'events')));
 const group=eventRefs[0].id;

 await runTransaction(db,async tx=>{
  const [bs,ms,ns,...units]=await Promise.all([
   tx.get(branch),tx.get(month),tx.get(nowMonth),...refs.map(r=>tx.get(r))
  ]);
  if(!bs.exists()||units.some(u=>!u.exists()))throw new Error('據點或倉位不存在');
  const b=bs.data();
  if(b.importing)throw new Error('據點正在匯入');
  if(ms.data()?.source==='import')throw new Error('該月已匯入歷史 KPI，不能新增異動');

  const rows=units.map(u=>u.data()!);
  rows.forEach((u,i)=>{
   const expected=i===0&&data.type==='transferOut'?'rented':'vacant';
   if(u.archived||u.missing||u.status!==expected||Boolean(u.leasePeriod)!==(expected==='rented'))throw new Error('倉位狀態已變更，請重新選擇');
   if(u.lastEventDate&&date<u.lastEventDate)throw new Error('日期不得早於倉位上一筆異動');
  });

  const delta=local?0:data.type==='transferIn'?1:-1;
  const rented=b.rented+delta,vacant=b.vacant-delta;
  if(rented<0||vacant<0)throw new Error('倉位統計不一致');

  rows.forEach((u,i)=>{
   const type=i===0?data.type:'transferIn';
   const out=type==='transferOut';
   const newLease=out?parseLease(''):lease!;
   tx.update(refs[i],{
    ...newLease,
    status:out?'vacant':'rented',
    vacantSince:out?date:null,
    lastEventDate:date,
    lastEventId:eventRefs[i].id,
    updatedAt:time()
   });
   const price=priceSnapshot(u,date);
   tx.set(eventRefs[i],{
    code:refs[i].id,type,date,month:date.slice(0,7),
    activities:[],exitReason:'',exitCategory:'',
    transferGroup:group,
    transferMode:local?'local':'external',
    peerCode:local?refs[1-i].id:'',
    peerEventId:local?eventRefs[1-i].id:'',
    priceSnapshot:price,
    unitSnapshot:{
     dimensions:u.dimensions,volume:u.volume,
     price:price.price,note:u.note,...newLease
    },
    previousLease:previous(u),
    previousEventDate:u.lastEventDate||null,
    previousEventId:u.lastEventId||null,
    createdBy:uid,createdAt:time(),voided:false
   });
  });

  tx.update(branch,{rented,vacant,revision:b.revision+1,updatedAt:time()});
  tx.set(month,{
   source:'live',
   ...(data.type==='transferOut'?{transferOut:(ms.data()?.transferOut||0)+1}:{}),
   ...(data.type==='transferIn'||local?{transferIn:(ms.data()?.transferIn||0)+1}:{}),
   ...(date.slice(0,7)===taipeiDate().slice(0,7)?{
    total:b.total,rented,vacant,snapshotDate:taipeiDate()
   }:{}),
   updatedAt:time()
  },{merge:true});
  if(month.id!==nowMonth.id&&ns.data()?.source!=='import'){
   tx.set(nowMonth,{
    source:'live',total:b.total,rented,vacant,
    snapshotDate:taipeiDate(),updatedAt:time()
   },{merge:true});
  }
 });
}

export async function undoTransfer(data:any){
 const branch=doc(db,'branches',key(data.branchId));
 const eventRef=doc(branch,'events',key(data.eventId));
 const uid=auth.currentUser?.uid;
 if(!uid)throw new Error('請先登入');

 await runTransaction(db,async tx=>{
  const first=await tx.get(eventRef);
  if(!first.exists())throw new Error('轉倉紀錄不存在');
  const e=first.data();
  const events=[{ref:eventRef,data:e}];
  if(e.transferMode==='local'){
   const peerRef=doc(branch,'events',key(e.peerEventId));
   const peer=await tx.get(peerRef);
   if(!peer.exists()||peer.data().transferGroup!==e.transferGroup)throw new Error('配對的轉倉紀錄不一致');
   events.push({ref:peerRef,data:peer.data()});
  }
  const month=doc(branch,'months',e.month);
  const nowMonth=doc(branch,'months',taipeiDate().slice(0,7));
  const units=events.map(x=>doc(branch,'units',x.data.code));
  const [bs,ms,ns,...us]=await Promise.all([
   tx.get(branch),tx.get(month),tx.get(nowMonth),...units.map(r=>tx.get(r))
  ]);
  if(!bs.exists()||bs.data().importing||ms.data()?.source!=='live')throw new Error('據點正在匯入或此月份不能撤銷');

  let delta=0;
  const counts:any={};
  events.forEach((x,i)=>{
   const u=us[i].data(),out=x.data.type==='transferOut';
   if(!['transferOut','transferIn'].includes(x.data.type)||x.data.voided||!u||u.archived||u.missing||u.lastEventId!==x.ref.id||u.status!==(out?'vacant':'rented'))throw new Error('轉倉後已有其它異動，不能撤銷；同店轉倉須兩間倉位皆為最後一筆異動');
   if(!Number.isInteger(ms.data()?.[x.data.type])||ms.data()![x.data.type]<1)throw new Error('轉倉統計不一致');
   delta+=out?1:-1;
   counts[x.data.type]=ms.data()![x.data.type]-1;
  });

  const b=bs.data(),rented=b.rented+delta,vacant=b.vacant-delta;
  if(rented<0||vacant<0)throw new Error('倉位統計不一致');
  events.forEach((x,i)=>{
   const out=x.data.type==='transferOut';
   tx.update(units[i],{
    ...x.data.previousLease,
    status:out?'rented':'vacant',
    lastEventId:x.data.previousEventId,
    lastEventDate:x.data.previousEventDate,
    updatedAt:time()
   });
   tx.update(x.ref,{
    voided:true,voidedBy:uid,voidedAt:time(),voidMode:'rollback'
   });
  });
  tx.update(branch,{rented,vacant,revision:b.revision+1,updatedAt:time()});
  tx.set(month,{
   ...counts,
   ...(month.id===nowMonth.id?{
    total:b.total,rented,vacant,snapshotDate:taipeiDate()
   }:{}),
   updatedAt:time()
  },{merge:true});
  if(month.id!==nowMonth.id&&ns.data()?.source!=='import'){
   tx.set(nowMonth,{
    source:'live',total:b.total,rented,vacant,
    snapshotDate:taipeiDate(),updatedAt:time()
   },{merge:true});
  }
 });
}

// storeasy-transfers-v1
