import {collection,doc,getDoc,getDocs,query,where,runTransaction,serverTimestamp} from 'firebase/firestore';
import {auth,db} from './firebase';
import {normalizeUnits,taipeiDate,validDate} from './domain.js';
import {parseLease} from './lease.js';
import {pricingUpdate} from './pricing.js';

export const renewalKey=(u:any)=>`${u.code}_${u.leaseStart}_${u.leaseEnd}`;

export function pendingRecord(unit:any,date:string,uid:string,source=''){
 return {
  code:unit.code,
  leasePeriod:unit.leasePeriod,
  leaseStart:unit.leaseStart,
  leaseEnd:unit.leaseEnd,
  status:'pending',
  observedDate:date,
  source,
  createdBy:uid,
  createdAt:serverTimestamp(),
  updatedBy:uid,
  updatedAt:serverTimestamp(),
  eventId:null,
  paymentMonth:null,
  paymentDate:null,
  unitSnapshot:{
   dimensions:unit.dimensions,
   volume:unit.volume,
   price:unit.price,
   note:unit.note,
   leasePeriod:unit.leasePeriod,
   leaseStart:unit.leaseStart,
   leaseEnd:unit.leaseEnd
  }
 };
}

function signed(){
 const uid=auth.currentUser?.uid;
 if(!uid)throw new Error('請先登入');
 return uid;
}

export async function matchingRenewals(branchId:string,code:string,period:string){
 const normalized=parseLease(period).leasePeriod;
 const rows=await getDocs(query(
  collection(db,'branches',branchId,'events'),
  where('code','==',code)
 ));
 return rows.docs.filter(d=>{
  const e=d.data();
  return e.type==='renew'&&!e.voided
   &&parseLease(e.unitSnapshot?.leasePeriod||'').leasePeriod===normalized;
 }).map(d=>({id:d.id,...d.data()} as any));
}

export async function savePendingUnit(data:any){
 const uid=signed();
 const unit=normalizeUnits([{...data,price:Number(data.price||0)}])[0];
 const date=taipeiDate();
 if(!unit.leasePeriod)throw new Error('待收款續約必須填寫租期');

 const b=doc(db,'branches',data.branchId);
 const u=doc(b,'units',unit.code);
 const p=doc(b,'pendingRenewals',renewalKey(unit));
 const matches=await matchingRenewals(data.branchId,unit.code,unit.leasePeriod);

 if(matches.length>1&&!data.pendingEventId)
  throw new Error('此租期有多筆續約紀錄，請在待收款選項中選擇要更正的那一筆');

 const match=matches.find(e=>e.id===data.pendingEventId)
  ||(matches.length===1?matches[0]:null);

 if(data.pendingEventId&&!match)
  throw new Error('所選續約紀錄已變更，請重新開啟編輯');

 await runTransaction(db,async t=>{
  const [bs,us,ps]=await Promise.all([t.get(b),t.get(u),t.get(p)]);

  if(!bs.exists()||bs.data().importing||us.data()?.status!=='rented')
   throw new Error('倉位已變更或據點正在匯入，請重新開啟編輯');

  const existing=ps.data();
  if(existing?.status==='paid')
   throw new Error('此租期已確認收款，請先在異動紀錄撤銷該次收款確認');

  const e=match?doc(b,'events',match.id):null;
  const es=e?await t.get(e):null;
  const event=es?.data();
  const m=event?doc(b,'months',event.month):null;
  const ms=m?await t.get(m):null;

  if(event&&(
   event.voided||event.type!=='renew'||event.code!==unit.code
   ||parseLease(event.unitSnapshot?.leasePeriod||'').leasePeriod!==unit.leasePeriod
  ))throw new Error('續約紀錄已變更，請重新開啟編輯');

  const next={
   ...us.data(),...unit,
   ...pricingUpdate(us.data(),unit,date,bs.data().inventoryDate)
  };

  t.set(u,{...next,updatedAt:serverTimestamp()});

  if(!existing)t.set(p,{
   ...pendingRecord(next,date,uid,'編輯標記'),
   reclassifiedEventId:match?.id||null
  });

  if(event&&e){
   t.update(e,{
    voided:true,
    voidMode:'paymentPending',
    voidedBy:uid,
    voidedAt:serverTimestamp(),
    pendingId:p.id
   });
   if(ms?.data()?.source!=='import'&&event.kpiCounted!==false){
    if(!(ms?.data()?.renew>0))
     throw new Error('原月份續約數不一致，無法自動更正，請先核對');
    t.set(m!,{
     renew:ms!.data()!.renew-1,
     updatedAt:serverTimestamp()
    },{merge:true});
   }
  }

  t.update(b,{
   revision:bs.data().revision+1,
   updatedAt:serverTimestamp()
  });
 });
 return {};
}

export async function confirmRenewalPayment(data:any){
 const uid=signed();
 const date=data.date||taipeiDate();
 const month=String(data.month||'');

 if(!validDate(date)||date>taipeiDate()
  ||!/^20\d{2}-(0[1-9]|1[0-2])$/.test(month))
  throw new Error('請填寫正確的收款日期及統計月份');

 const b=doc(db,'branches',data.branchId);
 const p=doc(b,'pendingRenewals',data.pendingId);
 const m=doc(b,'months',month);
 const e=doc(collection(b,'events'));

 await runTransaction(db,async t=>{
  const [bs,ps,ms]=await Promise.all([t.get(b),t.get(p),t.get(m)]);
  if(!bs.exists()||bs.data().importing)
   throw new Error('據點正在匯入，請稍後再試');

  const r=ps.data();
  if(!r)throw new Error('待收款紀錄不存在');
  if(r.status==='paid')return;

  const counted=ms.data()?.source!=='import';

  t.set(e,{
   code:r.code,type:'renew',date,month,activities:r.unitSnapshot.activities||[],
   unitSnapshot:r.unitSnapshot,
   priceSnapshot:{price:r.unitSnapshot.price},
   previousLease:{
    leasePeriod:r.leasePeriod,
    leaseStart:r.leaseStart,
    leaseEnd:r.leaseEnd
   },
   previousEventId:null,
   previousEventDate:null,
   paymentConfirmation:true,
   pendingId:p.id,
   kpiCounted:counted,
   createdBy:uid,
   createdAt:serverTimestamp(),
   voided:false
  });

  t.update(p,{
   status:'paid',
   eventId:e.id,
   paymentMonth:month,
   paymentDate:date,
   updatedBy:uid,
   updatedAt:serverTimestamp()
  });

  if(counted)t.set(m,{
   source:'live',
   renew:(ms.data()?.renew||0)+1,
   updatedAt:serverTimestamp()
  },{merge:true});

  t.update(b,{
   revision:bs.data().revision+1,
   updatedAt:serverTimestamp()
  });
 }).catch(async error=>{
  if(error.code==='permission-denied'
   &&(await getDoc(p)).data()?.status==='paid')return;
  throw error;
 });
 return {};
}

export async function undoRenewalPayment(data:any){
 const uid=signed();
 const b=doc(db,'branches',data.branchId);
 const e=doc(b,'events',data.eventId);

 await runTransaction(db,async t=>{
  const [bs,es]=await Promise.all([t.get(b),t.get(e)]);
  const event=es.data();

  if(!bs.exists()||bs.data().importing
   ||!event?.paymentConfirmation||event.voided)
   throw new Error('收款紀錄已變更或據點正在匯入');

  const p=doc(b,'pendingRenewals',event.pendingId);
  const m=doc(b,'months',event.month);
  const [ps,ms]=await Promise.all([t.get(p),t.get(m)]);

  if(ps.data()?.eventId!==e.id||ps.data()?.status!=='paid')
   throw new Error('待收款紀錄已變更');

  if(ms.data()?.source!=='import'&&event.kpiCounted){
   if(!(ms.data()?.renew>0))
    throw new Error('續約數不一致，請先核對');
   t.set(m,{
    renew:ms.data()!.renew-1,
    updatedAt:serverTimestamp()
   },{merge:true});
  }

  t.update(e,{
   voided:true,
   voidMode:'paymentPending',
   voidedBy:uid,
   voidedAt:serverTimestamp()
  });
  t.update(p,{
   status:'pending',
   eventId:null,
   paymentMonth:null,
   paymentDate:null,
   updatedBy:uid,
   updatedAt:serverTimestamp()
  });
  t.update(b,{
   revision:bs.data().revision+1,
   updatedAt:serverTimestamp()
  });
 });
 return {};
}

export async function deletePendingRenewal(data:any){
 const uid=auth.currentUser?.uid;
 if(!uid)throw new Error('請先登入');

 const b=doc(db,'branches',data.branchId);
 const p=doc(b,'pendingRenewals',data.pendingId);

 await runTransaction(db,async tx=>{
  const [bs,ps]=await Promise.all([tx.get(b),tx.get(p)]);

  if(!bs.exists()||bs.data().importing)
   throw new Error('據點不存在或正在匯入，請稍後再試');

  if(!ps.exists())return;

  if(ps.data().status!=='pending')
   throw new Error('此筆已確認收款，請重新整理；如需更正收款請從異動紀錄撤銷');

  tx.delete(p);
  tx.update(b,{
   revision:bs.data().revision+1,
   updatedAt:serverTimestamp()
  });
 });

 return {};
}
