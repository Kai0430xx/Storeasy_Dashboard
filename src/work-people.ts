import {useEffect,useRef,useState} from 'react';
import {collection,doc,onSnapshot,writeBatch} from 'firebase/firestore';
import {db} from './firebase';
import {WorkRow,workError} from './work-tasks';

export function useWorkPeople(profile:WorkRow,users:WorkRow[]=[]){
 const [people,setPeople]=useState<WorkRow[]>([]),[loaded,setLoaded]=useState(false),[error,setError]=useState('');
 const syncing=useRef(false),mounted=useRef(true);
 const [syncVersion,setSyncVersion]=useState(0);
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
 useEffect(()=>{
  setPeople([]);setLoaded(false);setError('');
  return onSnapshot(collection(db,'workPeople'),{includeMetadataChanges:true},s=>{
   setPeople(s.docs.map(d=>({id:d.id,...d.data()})));
   if(!s.metadata.fromCache)setLoaded(true);
  },e=>setError(workError(e)));
 },[profile.role]);
 const sourceKey=JSON.stringify(users.map(u=>[u.id,u.username]).sort());
 const peopleKey=JSON.stringify(people.map(p=>[p.id,p.username]).sort());
 useEffect(()=>{
  if(!loaded||!['admin','supervisor'].includes(profile.role)||!users.length||syncing.current)return;
  const known=new Map(people.map(p=>[p.id,p.username]));
  const missing=users.filter(u=>u.id&&typeof u.username==='string'&&known.get(u.id)!==u.username);
  if(!missing.length){setError('');return;}
  syncing.current=true;
  (async()=>{
   let success=false;
   try{
    for(let i=0;i<missing.length;i+=10){
     if(!mounted.current)return;
     const batch=writeBatch(db);
     for(const u of missing.slice(i,i+10))batch.set(doc(db,'workPeople',u.id),{username:u.username});
     await batch.commit();
    }
    success=true;
    if(mounted.current)setError('');
   }catch(e:any){
    if(mounted.current)setError('帳號名稱同步失敗：'+workError(e));
   }finally{
    syncing.current=false;
    if(success&&mounted.current)setSyncVersion(n=>n+1);
   }
  })();
 },[loaded,profile.role,sourceKey,peopleKey,syncVersion]);
 const names=[...new Set(people.map(p=>String(p.username)))].sort((a,b)=>a.localeCompare(b,'zh-Hant'));
 return {
  names,
  options:people.filter(p=>p.username).sort((a,b)=>String(a.username).localeCompare(String(b.username),'zh-Hant')),
  error
 };
}

// storeasy-work-team-v1
