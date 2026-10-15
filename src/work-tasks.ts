import {useEffect,useState} from 'react';
import {collection,doc,query,where,onSnapshot,runTransaction,serverTimestamp,Timestamp,orderBy,limit,getDocs} from 'firebase/firestore';
import {auth,db} from './firebase';
export type WorkRow=Record<string,any>;
export const workRoles=['admin','supervisor','manager'];
export const isWorkQuota=(error:any):boolean=>String(error?.code||'').includes('resource-exhausted')||/resource-exhausted|quota|額度/i.test(String(error?.message||error||''));
export function workError(error:any):string {
 if(typeof error==='string')return error;
 const code=String(error?.code||'unknown');
 const message=String(error?.message||'操作失敗');
 if(isWorkQuota(error))return `Firebase 仍回傳額度限制（${code}）：${message}。若已升級，請按「重新連線」重試；這段提示不代表目前一定是免費方案。`;
 if(code.includes('permission'))return `操作遭拒（${code}）：請確認最新 Firestore 規則已發布，且你仍有此據點權限。`;
 return `${message}（${code}）`;
}
export const stamp=(v:any):number=>v?.toMillis?.()||0;
export function unreadThreads(task:WorkRow,receipt?:WorkRow,uid=auth.currentUser?.uid){
 return Object.keys(task.signals||{}).filter(thread=>Object.entries(task.signals[thread]).some(([actor,time])=>actor!==uid&&stamp(time)>stamp(receipt?.seen?.[thread])));
}
export function useWorkTasks(profile:WorkRow|null){
 const [tasks,setTasks]=useState<WorkRow[]>([]),[reads,setReads]=useState<Record<string,WorkRow>>({}),[error,setError]=useState('');
 const [reconnect,setReconnect]=useState(0);
 const uid=auth.currentUser?.uid;
 useEffect(()=>{
  setTasks([]);setReads({});setError('');if(!uid||!profile||!workRoles.includes(profile.role))return;
  const parts=new Map<number,WorkRow[]>();const stops:(()=>void)[]=[];const scopes:any[]=[];
  if(['admin','supervisor'].includes(profile.role))scopes.push(collection(db,'workTasks'));
  else for(let i=0;i<(profile.branchIds||[]).length;i+=30)scopes.push(query(collection(db,'workTasks'),where('branchIds','array-contains-any',profile.branchIds.slice(i,i+30))));

  if(profile.role==='manager')scopes.push(query(collection(db,'workTasks'),where('createdBy','==',uid)));
  scopes.forEach((q,i)=>stops.push(onSnapshot(q,(s:any)=>{parts.set(i,s.docs.map((d:any)=>({id:d.id,...d.data()})));setTasks([...new Map([...parts.values()].flat().concat([...((parts as any).assigned?.values()||[])]).map(t=>[t.id,t])).values()]);},(e:any)=>setError(workError(e)))));
  if(profile.role==='manager'){
   const assigned=new Map<string,WorkRow>(),watchers=new Map<string,()=>void>();
   const publish=()=>setTasks([...new Map([...parts.values()].flat().concat([...assigned.values()]).map(t=>[t.id,t])).values()]);
   stops.push(onSnapshot(query(collection(db,'workTaskAccess'),where('uid','==',uid)),snapshot=>{
    const active=new Set(snapshot.docs.filter(d=>d.data().active).map(d=>String(d.data().taskId)));
    for(const [id,stop] of watchers)if(!active.has(id)){stop();watchers.delete(id);assigned.delete(id);}
    for(const id of active)if(!watchers.has(id))watchers.set(id,onSnapshot(doc(db,'workTasks',id),snapshot=>{if(snapshot.exists())assigned.set(id,{id,...snapshot.data()});else assigned.delete(id);publish();},e=>{assigned.delete(id);publish();setError(workError(e));}));
    publish();
   },e=>setError(workError(e))));
   stops.push(()=>watchers.forEach(stop=>stop()));
   (parts as any).assigned=assigned;
  }
  stops.push(onSnapshot(query(collection(db,'workReads'),where('uid','==',uid)),s=>setReads(Object.fromEntries(s.docs.map(d=>[d.data().taskId,d.data()]))),e=>setError(workError(e))));
  return()=>stops.forEach(s=>s());
 },[uid,profile?.role,JSON.stringify(profile?.branchIds),reconnect]);
 return {tasks,reads,error,retry:()=>{setError('');setReconnect(n=>n+1);},hasUnread:tasks.some(t=>unreadThreads(t,reads[t.id]).some(thread=>!t.deleted||thread==='main'))};
}
function actor(profile:WorkRow){if(!auth.currentUser)throw new Error('請重新登入');return {uid:auth.currentUser.uid,name:profile.username||'未命名帳號'};}
function fields(input:WorkRow){
 const result={category:String(input.category||'其它'),title:String(input.title||'').trim(),description:String(input.description||'').trim(),assignee:String(input.assignee||'').trim(),directAssigneeIds:[...new Set<string>(input.directAssigneeIds||[])].sort(),due:input.due||'',priority:input.priority||'normal'};
 if(!result.category||result.category.length>30||result.category.includes('/'))throw new Error('分類不合法');
 if(!result.title||result.title.length>120)throw new Error('標題須為1～120字');
 if(result.directAssigneeIds.length>100||result.directAssigneeIds.some(id=>typeof id!=='string'||!id||id.includes('/')))throw new Error('指派對象不合法或超過100人');
 if(result.description.length>5000||result.assignee.length>80)throw new Error('內容最多5000字，負責人最多80字');
 return result;
}
async function assignmentWrites(tx:any,taskId:string,thread:string,before:any,after:any,actionId:string,actorUid:string){
 const oldIds=new Set<string>(before&&!before.deleted?before.directAssigneeIds||[]:[]);
 const newIds=new Set<string>(after&&!after.deleted?after.directAssigneeIds||[]:[]);
 const changed=[...new Set([...oldIds,...newIds])].filter(uid=>oldIds.has(uid)!==newIds.has(uid));
 const writes:any[]=[];
 for(const uid of changed){
  const ref=doc(db,'workTaskAccess',`${uid}_${taskId}`),snapshot=await tx.get(ref);
  const oldSources:string[]=snapshot.data()?.sources||[];
  const sources=newIds.has(uid)?[...new Set([...oldSources,thread])]:oldSources.filter(source=>source!==thread);
  writes.push([ref,{uid,taskId,sources,primaryThread:sources[0]||'',active:sources.length>0,updatedBy:actorUid,updatedAt:serverTimestamp(),lastActionId:actionId}]);
 }
 return writes;
}
export async function createWorkTasks(profile:WorkRow,input:WorkRow){
 const who=actor(profile),ids=[...new Set<string>(input.branchIds)];if(!ids.length||ids.length>100)throw new Error('請選擇1～100個據點');
 const groups=input.mode==='separate'?ids.map(id=>[id]):[ids];let created=0;
 try{for(const branchIds of groups){
  const ref=doc(collection(db,'workTasks')),audit=doc(collection(ref,'history'));
  const entry={...fields(input),branchIds,branchNames:Object.fromEntries(branchIds.map(id=>[id,input.branchNames[id]])),mode:input.mode==='shared'?'shared':'single',done:false,deleted:false,childCount:0,openChildren:0,revision:0,createdBy:who.uid,createdName:who.name,createdAt:serverTimestamp(),updatedAt:serverTimestamp(),completedBy:null,completedName:null,completedAt:null,lastActionId:audit.id,signals:{main:{[who.uid]:serverTimestamp()}}};
  await runTransaction(db,async tx=>{
   const access=await assignmentWrites(tx,ref.id,'main',null,entry,audit.id,who.uid);
   tx.set(ref,entry);
   for(const [target,value] of access)tx.set(target,value);
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
  if(r.purging)throw new Error('事項正在永久刪除，請完成清除後再操作');
  if(r.deleted&&action!=='restore')throw new Error('事項已移到垃圾桶');
  if(item&&(!target||target.deleted)&&action!=='itemRestore')throw new Error('子項目已刪除或不存在');
  const pending:any[]=[];
  let patch:WorkRow={},before:any=null,after:any=null,eventThread=thread,targetId=item?.id||root.id;
  if(action==='edit'){
   const updated=fields(input);if(input.expected&&Object.keys(input.expected).some(k=>JSON.stringify(input.expected[k]??null)!==JSON.stringify(target?.[k]??null)))throw new Error('內容已被其他人修改，請關閉視窗後重新開啟。');before=target;after={...target,...updated};
   if(item)pending.push([item,after]);else patch=updated;
  }else if(action==='complete'){
   if(!item&&input.done&&r.openChildren>0)throw new Error('請先完成全部子項目');
   if(Boolean(target?.done)===Boolean(input.done))throw new Error('完成狀態已被其他人變更，請重新確認');
   const completed={done:Boolean(input.done),completedBy:input.done?who.uid:null,completedName:input.done?who.name:null,completedAt:input.done?serverTimestamp():null};
   before=target;after={...target,...completed};
   if(item){pending.push([item,after]);patch.openChildren=r.openChildren+(input.done?-1:1);if(!input.done)Object.assign(patch,{done:false,completedBy:null,completedName:null,completedAt:null});}else patch=completed;
  }else if(action==='addItem'){
   if(r.childCount>=100)throw new Error('每個事項最多建立100個子項目（包含垃圾桶）');
   eventThread=newItem.id;targetId=newItem.id;
   after={...fields(input),done:false,deleted:false,createdBy:who.uid,createdName:who.name,createdAt:serverTimestamp(),completedBy:null,completedName:null,completedAt:null};
   pending.push([newItem,after]);patch={childCount:r.childCount+1,openChildren:r.openChildren+1,done:false,completedBy:null,completedName:null,completedAt:null};
  }else if(action==='delete'||action==='restore'){
   if(action==='restore'&&!['admin','supervisor'].includes(profile.role))throw new Error('僅主管與管理員可以還原');
   if(Boolean(r.deleted)===(action==='delete'))throw new Error('事項狀態已變更');
   before=r;patch={deleted:action==='delete'};after={...r,...patch};
  }else if(action==='itemDelete'||action==='itemRestore'){
   if(!item)throw new Error('請選擇子項目');if(action==='itemRestore'&&!['admin','supervisor'].includes(profile.role))throw new Error('僅主管與管理員可以還原');
   const deleted=action==='itemDelete';if(Boolean(target?.deleted)===deleted)throw new Error('子項目狀態已變更');
   before=target;after={...target,deleted};pending.push([item,after]);
   patch={openChildren:r.openChildren+(target?.done?0:deleted?-1:1)};
   if(!deleted&&!target?.done)Object.assign(patch,{done:false,completedBy:null,completedName:null,completedAt:null});
  }else if(action==='message'){
   const text=String(input.text||'').trim();if(!text||text.length>5000)throw new Error('訊息須為1～5000字');
   targetId=message.id;after={text,author:who.uid,authorName:who.name,createdAt:serverTimestamp(),edited:false,deleted:false};pending.push([message,after]);
  }else if(action==='messageEdit'||action==='messageDelete'){
   const m=oldMessage?.data();if(!m||m.author!==who.uid||m.deleted)throw new Error('只能修改或刪除自己尚未刪除的訊息');
   targetId=message.id;before=m;
   if(action==='messageEdit'){
    const text=String(input.text||'').trim();if(!text||text.length>5000)throw new Error('訊息須為1～5000字');after={...m,text,edited:true,editedAt:serverTimestamp()};
   }else after={...m,text:'',deleted:true,deletedAt:serverTimestamp()};
   pending.push([message,after]);
  }else throw new Error('不支援此操作');
  const signals={...r.signals,[eventThread]:{...r.signals?.[eventThread],[who.uid]:serverTimestamp()}};
  const access=['edit','addItem','itemDelete','itemRestore'].includes(action)?await assignmentWrites(tx,taskId,eventThread,before,after,audit.id,who.uid):[];
  const updated={...r,...patch,signals,revision:r.revision+1,updatedAt:serverTimestamp(),lastActionId:audit.id};
  for(const [target,value] of [...pending,...access])tx.set(target,value);
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

// storeasy-work-team-v1

// storeasy-work-categories-v1
