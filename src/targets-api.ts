import {runTransaction} from "./waiting-stock";
import {normalizeOtherGoals} from './other-goals.js';
import {collection,doc,getDoc,serverTimestamp} from 'firebase/firestore';
import {auth,db} from './firebase';
import {parseLease} from './lease.js';
import {taipeiDate,validDate} from './domain.js';
export async function saveGoal(branchId:string,period:string,values:any,preserveEmpty=false){
 if(!/^(20\d{2}|20\d{2}-(0[1-9]|1[0-2]))$/.test(period))throw new Error('目標期間不合法');
 const goal:any={};
 for(const k of ['occupancy','performance','referrals']){
  const v=values[k];goal[k]=v===''||v==null?null:Number(v);
  if(goal[k]!=null&&(!Number.isFinite(goal[k])||goal[k]<0||(k==='occupancy'&&goal[k]>100)||(k==='referrals'&&!Number.isInteger(goal[k]))))throw new Error('目標數值不合法');
 }
 const uid=auth.currentUser?.uid;if(!uid)throw new Error('請先登入');
 const ref=doc(db,'branches',branchId,'targets',period),audit=doc(collection(db,'branches',branchId,'targetHistory'));
 await runTransaction(db,async t=>{
  const [actor,old]=await Promise.all([t.get(doc(db,'users',uid)),t.get(ref)]);
  if(!['admin','supervisor'].includes(actor.data()?.role))throw new Error('只有主管或管理員能設定目標');
  if(preserveEmpty) {
    for(const k of ["occupancy","performance","referrals"]) {
      if(values[k] === "" || values[k] == null)
        goal[k] = old.data()?.[k] ?? null;
    }
  }
  goal.other=period.length===7?normalizeOtherGoals(values.other??old.data()?.other??{}):{};
  if(period.length===4)goal.referrals=null;
  const next={...goal,period,revision:(old.data()?.revision||0)+1,updatedBy:uid,updatedAt:serverTimestamp(),changeId:audit.id};
  t.set(ref,next);t.set(audit,{period,previous:old.data()||null,next,by:uid,createdAt:serverTimestamp()});
 });
}
export async function saveReferrals(branchId:string,month:string,items:any[]){
 if(!/^20\d{2}-(0[1-9]|1[0-2])$/.test(month)||month>taipeiDate().slice(0,7))throw new Error('轉介月份不合法');
 if(items.length>200)throw new Error('每月轉介最多 200 筆');
 const entries=items.map(item=>{
  const code=String(item.code||'').trim();if(!code||code.length>80||code.includes('/'))throw new Error('每筆轉介請填倉位編號');
  const lease=parseLease(item.leasePeriod);if(!lease.leasePeriod)throw new Error('每筆轉介請填租期');
  return {code,...lease};
 });
 if(new Set(entries.map(e=>e.code+'|'+e.leasePeriod)).size!==entries.length)throw new Error('轉介倉位與租期重複');
 const uid=auth.currentUser?.uid;if(!uid)throw new Error('請先登入');
 await runTransaction(db,async t=>{
  const goal=await t.get(doc(db,'branches',branchId,'targets',month));
  t.set(doc(db,'branches',branchId,'referrals',month),{month,count:entries.length,entries,updatedBy:uid,updatedAt:serverTimestamp(),targetRevision:goal.data()?.revision||0});
 });
}
export async function saveVacantSince(branchId:string,code:string,date:string){
 if(date&&(!validDate(date)||date>taipeiDate()))throw new Error('空倉起始日不合法');
 const ref=doc(db,'branches',branchId,'units',code);
 await runTransaction(db,async t=>{const s=await t.get(ref);if(s.data()?.status!=='vacant'||s.data()?.missing||s.data()?.archived)throw new Error('倉位已變更，請重新整理');t.update(ref,{vacantSince:date||null,updatedAt:serverTimestamp()});});
}

// storeasy-other-monthly-v1

// storeasy-annual-renew-backfill-v2
