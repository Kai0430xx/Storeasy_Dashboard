import {doc,writeBatch,serverTimestamp} from 'firebase/firestore';
import {auth,db} from './firebase';
import {renewTermKeys,validateRenewCounts} from './renewal-kpi.js';
import {taipeiDate} from './domain.js';
type Row=Record<string,any>;
export async function backfillRenewals(branchId:string,months:Row[],existing:Row[],filename:string){
 const uid=auth.currentUser?.uid;
 if(!uid)throw Error('請先登入');
 if(!branchId||branchId.includes('/')||!Array.isArray(months)||!months.length||months.length>240||!Array.isArray(existing)||!filename?.trim()||filename.length>255)throw Error('續約分項資料不合法');
 const lookup=new Map(existing.map(m=>[m.month||m.id,m]));
 const seen=new Set<string>(),changes:Row[]=[];
 for(const m of months){
  if(!/^20\d{2}-(0[1-9]|1[0-2])$/.test(m.month)||m.month>=taipeiDate().slice(0,7)||seen.has(m.month))throw Error('只能補齊不重複且已結算月份');
  seen.add(m.month);
  const saved=lookup.get(m.month);
  if(!saved||saved.source!=='import')throw Error(`${m.month} 沒有已匯入的 KPI，請使用一般匯入`);
  if(saved.renew!==m.renew)throw Error(`${m.month} 續約總筆數與資料庫不同，請先核對，確認要更新總筆數時使用一般匯入`);
  const counts=validateRenewCounts(m.renewByTerm,m.renew);
  if(!counts)throw Error(`${m.month} 未提供續約租期分項`);
  if(renewTermKeys.every(k=>counts[k]===null))continue;
  if(!saved.renewByTerm||renewTermKeys.some(k=>saved.renewByTerm[k]!==counts[k]))changes.push({month:m.month,counts});
 }
 if(changes.length){
  const batch=writeBatch(db);
  for(const m of changes)batch.update(doc(db,'branches',branchId,'months',m.month),{renewByTerm:m.counts,renewTermSourceFile:filename.trim(),updatedBy:uid,updatedAt:serverTimestamp()});
  await batch.commit();
 }
 return {updated:changes.length,unchanged:months.length-changes.length};
}
