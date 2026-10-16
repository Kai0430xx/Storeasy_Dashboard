
import {useEffect,useState} from 'react';
import {collection,onSnapshot,query,where} from 'firebase/firestore';
import {db} from './firebase';
import {markWorkRead,unreadThreads} from './work-tasks';
import NotificationCenter from './NotificationCenter';

export default function HeaderAlerts({
 uid,profile,branches,work,waiting,onWork,onWaiting
}:any){
 const global=['admin','supervisor'].includes(profile.role);
 const [assigned,setAssigned]=useState<string[]>([]);
 const [busy,setBusy]=useState('');
 const [error,setError]=useState('');

 useEffect(()=>{
  if(!global)return;
  return onSnapshot(
   query(collection(db,'workTaskAccess'),where('uid','==',uid)),
   s=>setAssigned(
    s.docs.filter(d=>d.data().active).map(d=>d.data().taskId)
   ),
   ()=>setAssigned([])
  );
 },[uid,global]);

 const tasks=work.tasks.filter((t:any)=>
  !global||(t.directAssigneeIds||[]).includes(uid)||assigned.includes(t.id)
 );

 const notices=tasks.flatMap((task:any)=>
  unreadThreads(task,work.reads[task.id])
   .filter(thread=>!task.deleted||thread==='main')
   .map(thread=>({task,thread}))
 );

 const rows=waiting.rows.filter((r:any)=>
  r.branchIds.some((id:string)=>(profile.branchIds||[]).includes(id))&&
  waiting.notification(r)
 );

 const count=new Set(notices.map((n:any)=>n.task.id)).size+rows.length;

 async function open(
  key:string,fn:()=>Promise<void>,
  navigate:()=>void,close:()=>void
 ){
  setBusy(key);setError('');
  try{
   await fn();
   navigate();
   close();
  }catch(e:any){
   setError(e.message||'無法開啟通知，請重試');
  }finally{
   setBusy('');
  }
 }

 return <NotificationCenter uid={uid} role={profile.role}
  unreadCount={count}
  inbox={close=><section className="notification-inbox"
   aria-label="未讀通知">
   <h3>未讀通知 · {count} 筆</h3>
   {!count&&<p>目前沒有未讀通知。</p>}

   {notices.map(({task,thread}:any)=>
    <button type="button" className="notification-inbox-row"
     disabled={!!busy} key={task.id+thread}
     onClick={()=>open(
      task.id,
      ()=>markWorkRead(task,thread),
      ()=>onWork(task,thread),
      close
     )}>
     <strong>待辦 · {task.title}</strong>
     <span>
      {task.branchIds.map((id:string)=>
       task.branchNames?.[id]||id).join('、')}
      {' · '}{thread==='main'?'主事項':'子項目'}
      {task.deleted?' · 垃圾桶':task.done?' · 已完成':''}
     </span>
    </button>
   )}

   {rows.map((row:any)=>
    <button type="button" className="notification-inbox-row"
     disabled={!!busy} key={row.id}
     onClick={()=>open(
      row.id,
      ()=>waiting.markRead(row),
      ()=>onWaiting(row),
      close
     )}>
     <strong>候補 · {row.name}</strong>
     <span>
      {row.branchIds.map((id:string)=>
       branches.find((b:any)=>b.id===id)?.name||id).join('、')}
      {' · '}
      {waiting.notification(row)==='red'
       ? '需求已到期':'新增候補或合適空倉'}
     </span>
    </button>
   )}

   {error&&<p role="alert">{error}</p>}
  </section>}/>;
}
