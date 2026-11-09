import {FieldValue} from 'firebase-admin/firestore';
import {createHash} from 'node:crypto';
import {calendarEnabled,globalCalendar,eventInput,eventFields,calendarMonths,visibleEvent,activeEvent,dateOK,addDays,dayDiff} from './calendar-domain.js';
const stamp=()=>FieldValue.serverTimestamp();
const hash=s=>createHash('sha256').update(s).digest('hex').slice(0,40);
const path=s=>typeof s==='string'&&/^[a-zA-Z0-9_-]{1,160}$/.test(s);
const fail=message=>{throw Error(message);};
export function createCalendarService(db){
 async function actor(uid){if(!uid||!path(uid))fail('請先登入');const p=(await db.doc('users/'+uid).get()).data();if(!calendarEnabled(p))fail('此帳號尚未核准使用日曆');return {uid,p};}
 async function inputs(tx,raw,ownerId,existingCategoryId=''){
  const value=eventInput(raw);value.viewerIds=value.viewerIds.filter(id=>id!==ownerId);
  const people=value.viewerIds.length?await tx.getAll(...value.viewerIds.map(id=>db.doc('users/'+id))):[];
  if(people.some(p=>!calendarEnabled(p.data())))fail('分享對象已停用或不存在，請重新選擇');
  value.audienceBranchIds=[...new Set(people.flatMap(p=>p.data().branchIds||[]))];
  if(value.categoryId){if(!path(value.categoryId))fail('分類不合法');const c=(await tx.get(db.doc('calendarCategories/'+value.categoryId))).data();if(!c||c.ownerId!==ownerId||c.archived&&value.categoryId!==existingCategoryId)fail('請選擇建立者的有效分類');value.categoryName=c.name;value.color=c.color;}
  else{value.categoryName='未分類';value.color='#2563eb';}
  return value;
 }
 function writeEvent(tx,ref,before,after){
  tx.set(ref,after);const next=new Set(calendarMonths(after));
  for(const month of calendarMonths(before||after))if(!next.has(month))tx.delete(db.doc(`calendarMonths/${month}/events/${ref.id}`));
  for(const month of next)tx.set(db.doc(`calendarMonths/${month}/events/${ref.id}`),{...after,id:ref.id});
 }
 async function canWork(tx,task,uid,p,id){if(!['admin','supervisor','manager'].includes(p.role))return false;if(globalCalendar(p)||task.createdBy===uid||(task.branchIds||[]).some(id=>(p.branchIds||[]).includes(id)))return true;return (await tx.get(db.doc(`workTaskAccess/${uid}_${id}`))).data()?.active===true;}
 async function workPatch(tx,e,value,uid,p){
  if(!e.taskId)return null;
  const ref=db.doc('workTasks/'+e.taskId),s=await tx.get(ref),task=s.data();
  if(!task||task.deleted||task.purging||!await canWork(tx,task,uid,p,e.taskId))fail('原待辦已刪除或你沒有修改權限，可選擇只修改日曆');
  if(task.title===value.title&&task.due===value.startDate)return null;
  const log=db.collection(`workTasks/${e.taskId}/history`).doc();
  const next={...task,title:value.title,due:value.startDate,revision:task.revision+1,lastActionId:log.id,updatedAt:stamp(),signals:{...task.signals,main:{...task.signals?.main,[uid]:stamp()}}};
  return ()=>{tx.set(ref,next);tx.set(log,{action:'edit',thread:'main',actor:uid,actorName:p.username||'',at:stamp(),revision:next.revision,targetId:e.taskId,done:null});tx.set(db.doc(`workTasks/${e.taskId}/versions/${log.id}`),{before:task,after:next});};
 }
 async function save(uid,p,data){
  if(!path(data.id)||!path(data.operationId))fail('操作編號不正確');
  const ref=db.doc('calendarEvents/'+data.id);
  return db.runTransaction(async tx=>{
   const s=await tx.get(ref),old=s.data();
   if(old&&old.ownerId!==uid)fail('只有建立者能直接修改，請提出修改申請');
   if(old?.lastOperationId===data.operationId)return {id:ref.id};
   if(old&&(!activeEvent(old)||old.revision!==data.revision))fail('行程已變更，請重新開啟');
   const eventBranchIds=old?.eventBranchIds||[];
   if(!old&&data.scopeBranchId){
    if(!path(data.scopeBranchId)||!globalCalendar(p)&&!(p.branchIds||[]).includes(data.scopeBranchId))fail('不能將行程建立在沒有權限的據點');
    const branch=(await tx.get(db.doc('branches/'+data.scopeBranchId))).data();if(!branch||branch.archived)fail('所選據點已停用或不存在');eventBranchIds.push(data.scopeBranchId);
   }
   const value=await inputs(tx,data.values,uid,old?.categoryId);
   const sync=data.syncTask&&old?.taskId?await workPatch(tx,old,value,uid,p):null;
   let source={};if(old?.taskId){const task=(await tx.get(db.doc('workTasks/'+old.taskId))).data();source={taskTitle:data.syncTask?value.title:task?.title||old.taskTitle,taskDue:data.syncTask?value.startDate:task?.due||old.taskDue};}
   const next={...old,...value,...source,ownerId:uid,ownerName:p.username||'',ownerBranchIds:[...new Set([...(p.branchIds||[]),...eventBranchIds,...value.audienceBranchIds])],eventBranchIds,revision:(old?.revision||0)+1,taskId:old?.taskId||'',done:old?.done||false,removed:false,sourceDeleted:false,lastOperationId:data.operationId,createdAt:old?.createdAt||stamp(),updatedAt:stamp()};
   if(sync)sync();writeEvent(tx,ref,old,next);return {id:ref.id};
  });
 }
 async function request(uid,p,data){
  if(!path(data.eventId)||!path(data.id))fail('申請編號不正確');
  return db.runTransaction(async tx=>{
   const e=(await tx.get(db.doc('calendarEvents/'+data.eventId))).data(),ref=db.doc('calendarRequests/'+data.id),existing=await tx.get(ref);
   if(!e||!activeEvent(e)||!visibleEvent(e,uid,p)||e.ownerId===uid)fail('無法申請修改此行程');
   if(existing.exists){if(existing.data().requesterId!==uid)fail('申請編號已使用');return {id:ref.id};}
   if(e.revision!==data.revision)fail('行程已變更，請重新開啟再申請');
   const proposed=await inputs(tx,data.values,e.ownerId,e.categoryId);
   if(eventFields.every(k=>JSON.stringify(k==='endDateUnset'?!!e[k]:e[k])===JSON.stringify(proposed[k])))fail('尚未修改任何欄位');
   tx.set(ref,{eventId:data.eventId,eventTitle:e.title,ownerId:e.ownerId,requesterId:uid,requesterName:p.username||'',baseRevision:e.revision,before:{...Object.fromEntries(eventFields.map(k=>[k,k==='endDateUnset'?!!e[k]:e[k]])),categoryName:e.categoryName},proposed,syncTask:!!data.syncTask,status:'pending',seen:false,createdAt:stamp()});return {id:ref.id};
  });
 }
 async function review(uid,p,data){
  if(!path(data.id)||!['approved','rejected'].includes(data.status))fail('審核資料不正確');
  return db.runTransaction(async tx=>{
   const ref=db.doc('calendarRequests/'+data.id),s=await tx.get(ref),r=s.data();if(!r||r.ownerId!==uid)fail('只有建立者能審核');if(r.status!=='pending')return {status:r.status};
   const eventRef=db.doc('calendarEvents/'+r.eventId),e=(await tx.get(eventRef)).data();
   let status=data.status,next=null,sync=null;
   if(status==='approved'){
    const requester=(await tx.get(db.doc('users/'+r.requesterId))).data();
    if(!e||!activeEvent(e)||e.revision!==r.baseRevision||!visibleEvent(e,r.requesterId,requester))status='stale';
    else{const value=await inputs(tx,r.proposed,uid,e.categoryId);sync=r.syncTask?await workPatch(tx,e,value,uid,p):null;next={...e,...value,ownerBranchIds:[...new Set([...(p.branchIds||[]),...(e.eventBranchIds||[]),...value.audienceBranchIds])],revision:e.revision+1,lastOperationId:'request_'+ref.id,updatedAt:stamp()};if(e.taskId){const task=(await tx.get(db.doc('workTasks/'+e.taskId))).data();next.taskTitle=r.syncTask?value.title:task?.title||e.taskTitle;next.taskDue=r.syncTask?value.startDate:task?.due||e.taskDue;}}
   }
   if(sync)sync();if(next)writeEvent(tx,eventRef,e,next);tx.update(ref,{status,reviewedAt:stamp(),seen:false});return {status};
  });
 }
 async function category(uid,data){
  if(!data.id&&!path(data.operationId))fail('操作編號不合法');
  const id=data.id||'cat_'+hash(uid+data.operationId);if(!path(id))fail('分類編號不合法');
  const name=String(data.name||'').trim(),color=String(data.color||'');if(!name||name.length>30||!/^#[\da-f]{6}$/i.test(color))fail('分類名稱須為1～30字，請選擇顏色');
  const ref=db.doc('calendarCategories/'+id);
  await db.runTransaction(async tx=>{const old=await tx.get(ref);if(old.exists&&old.data().ownerId!==uid)fail('只能管理自己的分類');tx.set(ref,{ownerId:uid,name,color,archived:!!data.archived,updatedAt:stamp()});});
  const events=await db.collection('calendarEvents').where('ownerId','==',uid).get();
  for(const d of events.docs.filter(d=>d.data().categoryId===id))await db.runTransaction(async tx=>{const s=await tx.get(d.ref),e=s.data();if(!e||e.ownerId!==uid||e.categoryId!==id)return;const next={...e,categoryName:name,color,revision:e.revision+1,updatedAt:stamp()};writeEvent(tx,d.ref,e,next);});return {id};
 }
 async function createWork(uid,p,data){
  if(!['admin','supervisor','manager'].includes(p.role)||!path(data.operationId))fail('沒有建立待辦權限');
  const raw=data.task||{};if(!Array.isArray(raw.branchIds)||!Array.isArray(raw.directAssigneeIds||[]))fail('據點或指派人員格式不合法');const branchIds=[...new Set(raw.branchIds||[])].sort();if(!branchIds.length||branchIds.length>100||branchIds.some(id=>!path(id)))fail('請選擇有效據點');
  const title=String(raw.title||'').trim(),description=String(raw.description||''),category=String(raw.category||'其它').trim(),due=String(raw.due||'');
  const directAssigneeIds=[...new Set(raw.directAssigneeIds||[])];
  if(!title||title.length>120||description.length>5000||!category||category.length>30||due&&!dateOK(due)||directAssigneeIds.length>100||directAssigneeIds.some(id=>!path(id)))fail('待辦欄位不合法');
  if(!['single','shared','separate'].includes(raw.mode)||raw.mode==='single'&&branchIds.length!==1)fail('發布方式不合法');
  const groups=raw.mode==='separate'?branchIds.map(id=>[id]):[branchIds];let count=0;
  for(const ids of groups){
   const id='cal_'+hash(uid+data.operationId+JSON.stringify(ids)),ref=db.doc('workTasks/'+id),eventRef=db.doc('calendarEvents/work_'+id);
   await db.runTransaction(async tx=>{
    const existing=await tx.get(ref);
    const inputFingerprint=hash(JSON.stringify({mode:raw.mode,title,description,category,due,priority:raw.priority||'normal',directAssigneeIds:[...directAssigneeIds].sort(),calendar:eventInput(raw.calendarDraft)}));
    if(existing.exists){const linked=(await tx.get(eventRef)).data();if(linked?.workInputFingerprint!==inputFingerprint)fail('本次發布已有完成項目，內容已改變；請先核對原待辦，避免重複建立');return;}
    const names={};for(const bid of ids){const b=(await tx.get(db.doc('branches/'+bid))).data();if(!b||b.archived)fail('據點已停用或不存在');names[bid]=b.name;}
    for(const assignee of directAssigneeIds){const target=(await tx.get(db.doc('users/'+assignee))).data();if(!['admin','supervisor','manager'].includes(target?.role))fail('待辦指派對象不支援此角色');}
    const values=await inputs(tx,raw.calendarDraft,uid),log=db.collection(`workTasks/${id}/history`).doc();
    const access=[];for(const assignee of directAssigneeIds){const a=db.doc(`workTaskAccess/${assignee}_${id}`);await tx.get(a);access.push(a);}
    const task={title,description,category,due,assignee:'',directAssigneeIds,priority:raw.priority==='urgent'?'urgent':'normal',branchIds:ids,branchNames:names,mode:raw.mode==='shared'?'shared':'single',done:false,deleted:false,childCount:0,openChildren:0,revision:0,createdBy:uid,createdName:p.username||'',createdAt:stamp(),updatedAt:stamp(),completedBy:null,completedName:null,completedAt:null,lastActionId:log.id,signals:{main:{[uid]:stamp()}}};
    tx.set(ref,task);tx.set(log,{action:'create',thread:'main',actor:uid,actorName:p.username||'',at:stamp(),revision:0,targetId:id,done:null});tx.set(db.doc(`workTasks/${id}/versions/${log.id}`),{before:null,after:task});
    for(const a of access)tx.set(a,{uid:a.id.slice(0,-id.length-1),taskId:id,sources:['main'],primaryThread:'main',active:true,updatedBy:uid,updatedAt:stamp(),lastActionId:log.id});
    const event={...values,title:values.title||title,ownerId:uid,ownerName:p.username||'',ownerBranchIds:[...new Set([...(p.branchIds||[]),...ids,...values.audienceBranchIds])],eventBranchIds:ids,revision:1,taskId:id,taskTitle:title,taskDue:due,workInputFingerprint:inputFingerprint,done:false,removed:false,sourceDeleted:false,createdAt:stamp(),updatedAt:stamp(),lastOperationId:data.operationId};writeEvent(tx,eventRef,null,event);
   });count++;
  }return {count};
 }
 async function action(uid,data={}){
  const {p}=await actor(uid);
  if(data.action==='directory'){const users=await db.collection('users').get();return {people:users.docs.filter(d=>calendarEnabled(d.data())).map(d=>({id:d.id,name:d.data().username||'未命名帳號'}))};}
  if(data.action==='categoryOptions'){
   if(!path(data.eventId)||!path(data.ownerId))fail('分類查詢不合法');
   const event=(await db.doc('calendarEvents/'+data.eventId).get()).data();
   if(!event||event.ownerId!==data.ownerId||!activeEvent(event)||!visibleEvent(event,uid,p))fail('沒有查看此行程分類的權限');
   const categories=await db.collection('calendarCategories').where('ownerId','==',data.ownerId).get();return {rows:categories.docs.map(d=>({id:d.id,...d.data()}))};
  }
  if(data.action==='save')return save(uid,p,data);
  if(data.action==='request')return request(uid,p,data);
  if(data.action==='review')return review(uid,p,data);
  if(data.action==='category')return category(uid,data);
  if(data.action==='createWork')return createWork(uid,p,data);
  if(data.action==='seen'){if(!path(data.id))fail('申請編號不合法');const ref=db.doc('calendarRequests/'+data.id);await db.runTransaction(async tx=>{const r=(await tx.get(ref)).data();if(!r||r.requesterId!==uid||r.status==='pending')fail('無法標記此申請');tx.update(ref,{seen:true});});return {};}
  if(data.action==='remove'){if(!path(data.id))fail('行程編號不合法');await db.runTransaction(async tx=>{const ref=db.doc('calendarEvents/'+data.id),e=(await tx.get(ref)).data();if(!e||e.ownerId!==uid)fail('只有建立者能刪除');if(e.revision!==data.revision)fail('行程已變更');writeEvent(tx,ref,e,{...e,removed:true,revision:e.revision+1,updatedAt:stamp()});});return {};}
  fail('不支援的日曆操作');
 }
 async function syncWork(taskId){
  const events=await db.collection('calendarEvents').where('taskId','==',taskId).get();
  for(const d of events.docs)await db.runTransaction(async tx=>{const e=(await tx.get(d.ref)).data(),t=(await tx.get(db.doc('workTasks/'+taskId))).data();if(!e)return;const next={...e};let changed=false;
   if(t){if(e.taskTitle!==t.title){next.title=t.title;next.taskTitle=t.title;changed=true;}if(e.taskDue!==t.due){next.taskDue=t.due||'';if(dateOK(t.due)){const n=dayDiff(e.startDate,t.due);next.startDate=t.due;next.endDate=addDays(e.endDate,n);}changed=true;}}
   const deleted=!t||!!t.deleted||!!t.purging,done=!!t?.done;if(deleted!==!!e.sourceDeleted||done!==!!e.done){next.sourceDeleted=deleted;next.done=done;changed=true;}
   if(changed){next.revision=e.revision+1;next.updatedAt=stamp();writeEvent(tx,d.ref,e,next);}
  });
 }
 async function syncOwner(uid){
  const [own,shared]=await Promise.all([db.collection('calendarEvents').where('ownerId','==',uid).get(),db.collection('calendarEvents').where('viewerIds','array-contains',uid).get()]);
  const all=[...new Map([...own.docs,...shared.docs].map(d=>[d.id,d])).values()];
  for(const d of all)await db.runTransaction(async tx=>{
   const e=(await tx.get(d.ref)).data();if(!e)return;
   const owner=(await tx.get(db.doc('users/'+e.ownerId))).data();
   const audience=e.viewerIds?.length?await tx.getAll(...e.viewerIds.map(id=>db.doc('users/'+id))):[];
   const audienceBranchIds=[...new Set(audience.filter(s=>calendarEnabled(s.data())).flatMap(s=>s.data().branchIds||[]))];
   const ids=[...new Set([...(owner?.branchIds||[]),...(e.eventBranchIds||[]),...audienceBranchIds])];
   if(JSON.stringify(e.ownerBranchIds)!==JSON.stringify(ids)||owner?.username&&owner.username!==e.ownerName)writeEvent(tx,d.ref,e,{...e,ownerBranchIds:ids,audienceBranchIds,ownerName:owner?.username||e.ownerName,revision:e.revision+1,updatedAt:stamp()});
  });
 }

 return {action,syncWork,syncOwner};
}
