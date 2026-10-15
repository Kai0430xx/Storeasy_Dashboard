import {useEffect,useRef,useState} from 'react';
import {collection,doc,onSnapshot,writeBatch} from 'firebase/firestore';
import {db} from './firebase';
import {compareBranches} from './branch-order.js';
import {WorkRow,workError} from './work-tasks';

export function useWorkBranches(profile:WorkRow,owned:WorkRow[]){
 const [rows,setRows]=useState<WorkRow[]>([]);
 const [ready,setReady]=useState(false);
 const [error,setError]=useState('');
 const [version,setVersion]=useState(0);
 const syncing=useRef(false);

 useEffect(()=>{
  setRows([]);
  setReady(false);
  setError('');
  return onSnapshot(
   collection(db,'workBranches'),
   {includeMetadataChanges:true},
   s=>{
    setRows(s.docs.map(d=>({id:d.id,...d.data()})));
    if(!s.metadata.fromCache)setReady(true);
   },
   e=>setError(workError(e))
  );
 },[profile.role]);

 const sourceKey=JSON.stringify(
  owned.map(b=>[b.id,b.name,!!b.archived])
 );
 const rowsKey=JSON.stringify(
  rows.map(b=>[b.id,b.name,!!b.archived])
 );

 useEffect(()=>{
  if(!ready||syncing.current)return;
  const known=new Map(rows.map(b=>[b.id,b]));
  const missing=owned.filter(b=>
   known.get(b.id)?.name!==b.name
   ||!!known.get(b.id)?.archived!==!!b.archived
  );
  if(!missing.length)return;

  syncing.current=true;
  (async()=>{
   let success=false;
   try{
    for(let i=0;i<missing.length;i+=10){
     const batch=writeBatch(db);
     for(const b of missing.slice(i,i+10)){
      batch.set(doc(db,'workBranches',b.id),{
       name:b.name,
       archived:!!b.archived
      });
     }
     await batch.commit();
    }
    success=true;
    setError('');
   }catch(e){
    setError(workError(e));
   }finally{
    syncing.current=false;
    if(success)setVersion(n=>n+1);
   }
  })();
 },[sourceKey,rowsKey,ready,version]);

 const all=new Map(rows.map(b=>[b.id,b]));
 for(const b of owned)all.set(b.id,b);

 return {
  branches:[...all.values()]
   .filter(b=>!b.archived)
   .sort(compareBranches),
  error,
  ready
 };
}
