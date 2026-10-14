import {useEffect,useState} from 'react';
import {collection,doc,query,where,onSnapshot,runTransaction,serverTimestamp,Timestamp,orderBy,limit,getDocs} from 'firebase/firestore';
import {auth,db} from './firebase';
export type WorkRow=Record<string,any>;
export const workRoles=['admin','supervisor','manager'];
export const stamp=(v:any):number=>v?.toMillis?.()||0;
export function unreadThreads(task:WorkRow,receipt?:WorkRow,uid=auth.currentUser?.uid){
 return Object.keys(task.signals||{}).filter(thread=>Object.entries(task.signals[thread]).some(([actor,time])=>actor!==uid&&stamp(time)>stamp(receipt?.seen?.[thread])));
}
export function useWorkTasks(profile:WorkRow|null){
 const [tasks,setTasks]=useState<WorkRow[]>([]),[reads,setReads]=useState<Record<string,WorkRow>>({}),[error,setError]=useState('');
 const uid=auth.currentUser?.uid;
 useEffect(()=>{
  setTasks([]);setReads({});setError('');if(!uid||!profile||!workRoles.includes(profile.role))return;
  const parts=new Map<number,WorkRow[]>();const stops:(()=>void)[]=[];const scopes:any[]=[];
  if(['admin','supervisor'].includes(profile.role))scopes.push(collection(db,'workTasks'));
  else for(let i=0;i<(profile.branchIds||[]).length;i+=30)scopes.push(query(collection(db,'workTasks'),where('branchIds','array-contains-any',profile.branchIds.slice(i,i+30))));
  scopes.forEach((q,i)=>stops.push(onSnapshot(q,(s:any)=>{parts.set(i,s.docs.map((d:any)=>({id:d.id,...d.data()})));setTasks([...new Map([...parts.values()].flat().map(t=>[t.id,t])).values()]);},(e:any)=>setError(e.message))));
  stops.push(onSnapshot(query(collection(db,'workReads'),where('uid','==',uid)),s=>setReads(Object.fromEntries(s.docs.map(d=>[d.data().taskId,d.data()]))),e=>setError(e.message)));
  return()=>stops.forEach(s=>s());
 },[uid,profile?.role,JSON.stringify(profile?.branchIds)]);
 return {tasks,reads,error,hasUnread:tasks.some(t=>unreadThreads(t,reads[t.id]).some(thread=>!t.deleted||thread==='main'))};
}
function actor(profile:WorkRow){if(!auth.currentUser)throw new Error('請重新登入');return {uid:auth.currentUser.uid,name:profile.username||'未命名帳號'};}
function fields(input:WorkRow){
 const result={title:String(input.title||'').trim(),description:String(input.description||'').trim(),assignee:String(input.assignee||'').trim(),due:input.due||'',priority:input.priority||'normal'};
 if(!result.title||result.title.length>120)throw new Error('標題須為1～120字');
 if(result.description.length>5000||result.assignee.length>80)throw new Error('內容最多5000字，負責人最多80字');
 return result;
}
export async function createWorkTasks(profile:WorkRow,input:WorkRow){
 const who=actor(profile),ids=[...new Set<string>(input.branchIds)];if(!ids.length||ids.length>100)throw new Error('請選擇1～100個據點');
 const groups=input.mode==='separate'?ids.map(id=>[id]):[ids];let created=0;
 try{for(const branchIds of groups){
  const ref=doc(collection(db,'workTasks')),audit=doc(collection(ref,'history'));
  const entry={...fields(input),branchIds,branchNames:Object.fromEntries(branchIds.map(id=>[id,input.branchNames[id]])),mode:input.mode==='shared'?'shared':'single',done:false,deleted:false,childCount:0,openChildren:0,revision:0,createdBy:who.uid,createdName:who.name,createdAt:serverTimestamp(),updatedAt:serverTimestamp(),completedBy:null,completedName:null,completedAt:null,lastActionId:audit.id,signals:{main:{[who.uid]:serverTimestamp()}}};
  await runTransaction(db,async tx=>{
   tx.set(ref,entry);
   tx.set(audit,{action:'create',thread:'main',actor:who.uid,actorName:who.name,at:serverTimestamp(),revision:0,targetId:ref.id,done:null});
   tx.set(doc(ref,'versions',audit.id),{before:null,after:entry});
  });created++;
 }}catch(e:any){throw new Error(`已成功發布 ${created} 份，其餘未完成：${e.message}。請勿對已成功的據點重複發布。`);}return created;
}
export async function workAction(profile:WorkRow,taskId:string,action:string,thread:string='main',input:WorkRow={}){
 const who=actor(profile),root=doc(db,'workTasks',taskId),audit=doc(collection(root,'history'));
 const item=thread==='main'?null:doc(root,'items',thread),newItem=doc(collection(root,'items'));
 const message=input.messageId?doc(root,'threads',thread,'messages',input.messageId):doc(collection(root,'threads',thread,'messages'));
 await runTransaction(db,async tx=>{
  const rs=await tx.get(root);if(!rs.exists())throw new Error('事項不存在');const r=rs.data();
  const sub=item?await tx.get(item):null,target=item?sub?.data():r;
  const oldMessage=action==='messageEdit'||action==='messageDelete'?await tx.get(message):null;
  if(r.deleted&&action!=='restore')throw new Error('事項已移到垃圾桶');
  if(item&&(!target||target.deleted)&&action!=='itemRestore')throw new Error('子項目已刪除或不存在');
  let patch:WorkRow={},before:any=null,after:any=null,eventThread=thread,targetId=item?.id||root.id;
  if(action==='edit'){
   const updated=fields(input);if(input.expected&&Object.keys(input.expected).some(k=>input.expected[k]!==target?.[k]))throw new Error('內容已被其他人修改，請關閉視窗後重新開啟。');before=target;after={...target,...updated};
   if(item)tx.set(item,after);else patch=updated;
  }else if(action==='complete'){
   if(!item&&input.done&&r.openChildren>0)throw new Error('請先完成全部子項目');
   if(Boolean(target?.done)===Boolean(input.done))throw new Error('完成狀態已被其他人變更，請重新確認');
   const completed={done:Boolean(input.done),completedBy:input.done?who.uid:null,completedName:input.done?who.name:null,completedAt:input.done?serverTimestamp():null};
   before=target;after={...target,...completed};
   if(item){tx.set(item,after);patch.openChildren=r.openChildren+(input.done?-1:1);if(!input.done)Object.assign(patch,{done:false,completedBy:null,completedName:null,completedAt:null});}else patch=completed;
  }else if(action==='addItem'){
   if(r.childCount>=100)throw new Error('每個事項最多建立100個子項目（包含垃圾桶）');
   eventThread=newItem.id;targetId=newItem.id;
   after={...fields(input),done:false,deleted:false,createdBy:who.uid,createdName:who.name,createdAt:serverTimestamp(),completedBy:null,completedName:null,completedAt:null};
   tx.set(newItem,after);patch={childCount:r.childCount+1,openChildren:r.openChildren+1,done:false,completedBy:null,completedName:null,completedAt:null};
  }else if(action==='delete'||action==='restore'){
   if(action==='restore'&&!['admin','supervisor'].includes(profile.role))throw new Error('僅主管與管理員可以還原');
   if(Boolean(r.deleted)===(action==='delete'))throw new Error('事項狀態已變更');
   before=r;patch={deleted:action==='delete'};after={...r,...patch};
  }else if(action==='itemDelete'||action==='itemRestore'){
   if(!item)throw new Error('請選擇子項目');if(action==='itemRestore'&&!['admin','supervisor'].includes(profile.role))throw new Error('僅主管與管理員可以還原');
   const deleted=action==='itemDelete';if(Boolean(target?.deleted)===deleted)throw new Error('子項目狀態已變更');
   before=target;after={...target,deleted};tx.set(item,after);
   patch={openChildren:r.openChildren+(target?.done?0:deleted?-1:1)};
   if(!deleted&&!target?.done)Object.assign(patch,{done:false,completedBy:null,completedName:null,completedAt:null});
  }else if(action==='message'){
   const text=String(input.text||'').trim();if(!text||text.length>5000)throw new Error('訊息須為1～5000字');
   targetId=message.id;after={text,author:who.uid,authorName:who.name,createdAt:serverTimestamp(),edited:false,deleted:false};tx.set(message,after);
  }else if(action==='messageEdit'||action==='messageDelete'){
   const m=oldMessage?.data();if(!m||m.author!==who.uid||m.deleted)throw new Error('只能修改或刪除自己尚未刪除的訊息');
   targetId=message.id;before=m;
   if(action==='messageEdit'){
    const text=String(input.text||'').trim();if(!text||text.length>5000)throw new Error('訊息須為1～5000字');after={...m,text,edited:true,editedAt:serverTimestamp()};
   }else after={...m,text:'',deleted:true,deletedAt:serverTimestamp()};
   tx.set(message,after);
  }else throw new Error('不支援此操作');
  const signals={...r.signals,[eventThread]:{...r.signals?.[eventThread],[who.uid]:serverTimestamp()}};
  const updated={...r,...patch,signals,revision:r.revision+1,updatedAt:serverTimestamp(),lastActionId:audit.id};
  if(eventThread==='main'&&!action.startsWith('message'))after=updated;
  tx.set(root,updated);
  tx.set(audit,{action,thread:eventThread,actor:who.uid,actorName:who.name,at:serverTimestamp(),revision:r.revision+1,targetId,done:action==='complete'?Boolean(after.done):null});
  tx.set(doc(root,'versions',audit.id),{before,after});
 });
}
export async function markWorkRead(task:WorkRow,thread:string){
 const uid=auth.currentUser?.uid;if(!uid)return;
 const latest=Math.max(0,...Object.entries(task.signals?.[thread]||{}).filter(([id])=>id!==uid).map(([,v])=>stamp(v)));
 if(!latest)return;
 const ref=doc(db,'workReads',`${uid}_${task.id}`);
 await runTransaction(db,async tx=>{const s=await tx.get(ref);if(stamp(s.data()?.seen?.[thread])>=latest)return;
  tx.set(ref,{uid,taskId:task.id,seen:{...s.data()?.seen,[thread]:Timestamp.fromMillis(latest)}});
 });
}
export async function loadWorkHistory(taskId:string){return (await getDocs(query(collection(db,'workTasks',taskId,'history'),orderBy('at','desc'),limit(100)))).docs.map(d=>({id:d.id,...d.data()}));}
