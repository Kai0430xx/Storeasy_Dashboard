import {useEffect,useState} from 'react';
import {collection,onSnapshot,query,where} from 'firebase/firestore';
import {auth,db} from './firebase';
import {workError} from './work-tasks';
import type {WorkRow} from './work-tasks';

export function useMyWorkScope(allTasks:WorkRow[],profile:WorkRow){
 const uid=auth.currentUser?.uid;
 const [scope,setScope]=useState('mine');
 const [access,setAccess]=useState<{uid:string;ids:string[]}>({uid:'',ids:[]});
 const [scopeError,setError]=useState('');

 useEffect(()=>{
  setScope('mine');
  setAccess({uid:uid||'',ids:[]});
  setError('');
  if(!uid)return;

  let active=true;
  const stop=onSnapshot(
   query(collection(db,'workTaskAccess'),where('uid','==',uid)),
   snapshot=>{
    if(active)setAccess({
     uid,
     ids:snapshot.docs.filter(d=>
      d.data().active&&
      (d.data().sources||[]).some((thread:string)=>thread!=='main')
     ).map(d=>String(d.data().taskId))
    });
   },
   error=>{
    if(active)setError('指派清單讀取失敗：'+workError(error));
   }
  );
  return()=>{active=false;stop();};
 },[uid]);

 const mine=(task:WorkRow)=>Boolean(uid)&&(
  (task.branchIds||[]).some((id:string)=>
   (profile.branchIds||[]).includes(id)
  )||
  (task.directAssigneeIds||[]).includes(uid)||
  access.uid===uid&&access.ids.includes(task.id)
 );

 return {
  scope,
  setScope,
  scopeError,
  tasks:scope==='all'?allTasks:allTasks.filter(mine)
 };
}

export function WorkScopePicker({scope,onChange}:{
 scope:string;
 onChange:(value:string)=>void;
}){
 return <label style={{
  display:'flex',
  flexDirection:'column',
  gap:6,
  minWidth:0,
  maxWidth:'100%'
 }}>
  待辦範圍
  <select aria-label="待辦範圍" value={scope}
   onChange={e=>onChange(e.target.value)}>
   <option value="mine">我的據點＋指派給我</option>
   <option value="all">全部可查看待辦</option>
  </select>
 </label>;
}
