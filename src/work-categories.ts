import {useEffect,useState} from 'react';
import {collection,doc,onSnapshot,setDoc,serverTimestamp,query,where,getDocs,getDoc,limit,writeBatch,runTransaction} from 'firebase/firestore';
import {auth,db} from './firebase';
import {WorkRow,workError} from './work-tasks';

export const defaultWorkCategories=['店務','工務','IT','行銷','其它'];

export function useWorkCategories(){
 const [custom,setCustom]=useState<string[]>([]),[error,setError]=useState('');
 useEffect(()=>onSnapshot(
  collection(db,'workCategories'),
  s=>setCustom(s.docs.map(d=>d.id).sort((a,b)=>a.localeCompare(b,'zh-Hant'))),
  e=>setError(workError(e))
 ),[]);
 return {
  options:[...defaultWorkCategories,...custom.filter(n=>!defaultWorkCategories.includes(n))],
  error
 };
}

export async function addWorkCategory(profile:WorkRow,name:string){
 name=name.trim();
 if(!['admin','supervisor'].includes(profile.role))throw new Error('僅主管與管理員可新增分類');
 if(!name||name.length>30||name.includes('/')||name==='.'||name==='..')throw new Error('分類須為1～30字，不能包含斜線');
 if(defaultWorkCategories.includes(name)||(await getDoc(doc(db,'workCategories',name))).exists())throw new Error('此分類已存在');
 await setDoc(doc(db,'workCategories',name),{
  name,
  createdBy:auth.currentUser!.uid,
  createdAt:serverTimestamp()
 });
}

export async function permanentlyDeleteWorkTask(profile:WorkRow,taskId:string){
 if(!['admin','supervisor'].includes(profile.role))throw new Error('僅主管與管理員可永久刪除');
 const root=doc(db,'workTasks',taskId);
 const data=await runTransaction(db,async tx=>{
  const s=await tx.get(root);
  if(!s.exists())throw new Error('事項不存在');
  const d=s.data();
  if(!d.deleted)throw new Error('請先將事項移到垃圾桶');
  if(!d.purging)tx.update(root,{purging:true});
  return d;
 });
 const children=await getDocs(collection(root,'items'));
 const threads=new Set([
  'main',
  ...Object.keys(data.signals||{}),
  ...children.docs.map(d=>d.id)
 ]);
 const clear=async(q:any)=>{
  for(;;){
   const s=await getDocs(query(q,limit(200)));
   if(s.empty)return;
   const batch=writeBatch(db);
   s.docs.forEach((d:any)=>batch.delete(d.ref));
   await batch.commit();
  }
 };
 // 根文件最後刪除，途中中斷可繼續清除。
 for(const thread of threads)await clear(collection(root,'threads',thread,'messages'));
 await clear(collection(root,'threads'));
 await clear(collection(root,'items'));
 await clear(collection(root,'history'));
 await clear(collection(root,'versions'));
 await clear(query(collection(db,'workTaskAccess'),where('taskId','==',taskId)));
 await clear(query(collection(db,'workReads'),where('taskId','==',taskId)));
 const batch=writeBatch(db);
 batch.delete(root);
 await batch.commit();
}

// storeasy-work-categories-v1
