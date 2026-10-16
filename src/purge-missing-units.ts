import {collection,doc,getDocs,query,where,deleteField,serverTimestamp} from 'firebase/firestore';
import {runTransaction,writeBatch} from './waiting-stock';
import {auth,db} from './firebase';
const running=new Map<string,Promise<void>>();
export function purgeMissingUnits(branchId:string){
 const uid=auth.currentUser?.uid;if(!uid||!branchId||branchId.includes('/'))return Promise.reject(new Error('據點或登入狀態不正確'));
 const key=uid+'/'+branchId;if(running.has(key))return running.get(key)!;
 const promise=(async()=>{
  const branch=doc(db,'branches',branchId),token=crypto.randomUUID();let locked=false;
  try{
   const pending=await getDocs(query(collection(branch,'units'),where('missing','==',true)));
   if(pending.empty)return;
   await runTransaction(db,async tx=>{const s=await tx.get(branch);if(!s.exists()||s.data().importing)throw new Error('據點正在匯入，請稍後重新整理');tx.update(branch,{importing:{operation:'purgeMissing',token,by:uid,startedAt:Date.now()},revision:s.data().revision+1});});locked=true;
   const rows=await getDocs(query(collection(branch,'units'),where('missing','==',true)));
   for(let i=0;i<rows.docs.length;i+=8){const batch=writeBatch(db);rows.docs.slice(i,i+8).forEach(s=>batch.delete(s.ref));await batch.commit();}
  }finally{
   if(locked)await runTransaction(db,async tx=>{const s=await tx.get(branch);if(s.data()?.importing?.token===token)tx.update(branch,{importing:deleteField(),revision:s.data()!.revision+1,updatedAt:serverTimestamp()});});
  }
 })().finally(()=>running.delete(key));running.set(key,promise);return promise;
}
