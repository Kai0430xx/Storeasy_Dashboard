from pathlib import Path
import re, datetime

root = Path(__file__).resolve().parents[1]
changes = {}

changes['src/NotificationCenter.tsx'] = r'''
import OwnNotificationBranches from './OwnNotificationBranches';
import {useEffect,useState,ReactNode} from 'react';
import {doc,onSnapshot} from 'firebase/firestore';
import {Bell,X} from 'lucide-react';
import {db} from './firebase';
import {
 currentDevice,disablePush,enablePush,iosDevice,
 notificationError,pushSupported,standalone,workerMessage,PushDevice
} from './push-client';
import './notifications.css';

export default function NotificationCenter({
 uid,role,unreadCount,inbox
}:{
 uid:string;
 role:string;
 unreadCount?:number;
 inbox?:(close:()=>void)=>ReactNode;
}){
 const [open,setOpen]=useState(false);
 const [device,setDevice]=useState<PushDevice|null>(currentDevice);
 const [active,setActive]=useState(false);
 const [count,setCount]=useState<number|null>(null);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 const supported=pushSupported();
 const needsInstall=iosDevice()&&!standalone();

 useEffect(()=>{
  setActive(false);setCount(null);
  if(!device||device.uid!==uid)return;
  return onSnapshot(doc(db,'pushDevices',device.deviceId),s=>{
   setActive(
    s.exists()&&s.data().uid===uid&&
    s.data().binding===device.binding&&
    pushSupported()&&Notification.permission==='granted'
   );
  },()=>setActive(false));
 },[uid,device?.deviceId,device?.binding]);

 useEffect(()=>{
  setCount(null);
  if(!active||!device)return;
  return onSnapshot(doc(db,'pushStatus',uid),s=>{
   const value=s.data();
   if(!value)return;
   setCount(value.count);
   void workerMessage('badge',{
    ...device,version:value.version,count:value.count
   }).catch(()=>{});
  });
 },[uid,active,device?.binding]);

 async function enable(){
  if(busy)return;
  setBusy(true);setError('');setNotice('');
  try{
   const value=await enablePush();
   setDevice(value);
   setNotice('此裝置已啟用背景通知');
  }catch(e){
   setError(notificationError(e));
  }finally{
   setBusy(false);
  }
 }

 async function disable(){
  if(busy)return;
  setBusy(true);setError('');setNotice('');
  try{
   await disablePush();
   setNotice('此裝置通知已停用');
  }catch(e){
   setError(notificationError(e));
  }finally{
   setDevice(null);setActive(false);setCount(null);setBusy(false);
  }
 }

 const total=unreadCount??count??0;

 return <>
  <button type="button" className="notification-settings-button"
   title="通知設定" aria-label="通知設定"
   onClick={()=>{setOpen(true);setError('');setNotice('');}}>
   <Bell size={18}/>
   {total>0&&<span>{total>99?'99+':total}</span>}
  </button>

  {open&&<div className="modal-backdrop">
   <section className="modal notification-modal"
    role="dialog" aria-modal="true" aria-label="通知設定">
    <div className="modal-heading">
     <h2>通知設定</h2>
     <button type="button" aria-label="關閉"
      disabled={busy} onClick={()=>setOpen(false)}>
      <X size={20}/>
     </button>
    </div>

    {inbox?.(()=>setOpen(false))}

    <p>
     沒開網頁時，也能收到待辦與所屬據點候補提醒。
     桌面圖示數字依系統支援顯示，每筆只算一次。
    </p>

    <p className="hint">
     {role==='manager'
      ? '候補據點包含所屬分店才會提醒；待辦依可查看事項的未讀紅點。'
      : '待辦只有明確指派給你才通知；候補只通知你負責的據點，包含配對黃點與到期紅點。'}
    </p>

    {['admin','supervisor'].includes(role)&&
     <OwnNotificationBranches uid={uid}/>}

    <p className="notification-state">
     此裝置：<strong>{active?'已啟用':'尚未啟用'}</strong>
     {active&&count!==null&&<span> · 未讀 {count} 筆</span>}
    </p>

    {needsInstall&&<div className="alert">
     iPhone 請先用 Safari 開啟網站，按分享 → 加入主畫面，
     再從桌面圖示開啟本網站並啟用通知。需 iOS 16.4 以上。
    </div>}

    {!supported&&!needsInstall&&<div className="alert">
     目前瀏覽器不支援背景通知，
     請改用支援的瀏覽器或加入主畫面後再試。
    </div>}

    {supported&&Notification.permission==='denied'&&
     <p className="hint">
      通知權限已關閉，請到手機或瀏覽器的通知設定重新允許。
     </p>}

    <p className="hint">
     通知只顯示未讀筆數，不放客人個資或訊息內容。
     系統可能因專注模式、網路或省電設定延遲；
     此設定只影響這個裝置。
    </p>

    {error&&<p role="alert" className="alert error">{error}</p>}
    {notice&&<p role="status" className="alert success">{notice}</p>}

    <div className="notification-actions">
     <button type="button" className="primary"
      disabled={busy||!supported||needsInstall} onClick={enable}>
      {busy?'處理中…':active?'重新連線通知':'開啟此裝置通知'}
     </button>
     <button type="button" className="secondary"
      disabled={busy||!device||device.uid!==uid} onClick={disable}>
      停用此裝置通知
     </button>
    </div>
   </section>
  </div>}
 </>;
}
'''

changes['src/OwnNotificationBranches.tsx'] = r'''
import {useEffect,useState} from 'react';
import {collection,doc,onSnapshot} from 'firebase/firestore';
import {db} from './firebase';
import {
 saveOwnNotificationBranches,notificationError
} from './push-client';

export default function OwnNotificationBranches({uid}:{uid:string}){
 const [branches,setBranches]=useState<{id:string;name:string}[]>([]);
 const [selected,setSelected]=useState<string[]>([]);
 const [saved,setSaved]=useState<string[]>([]);
 const [loaded,setLoaded]=useState(false);
 const [dirty,setDirty]=useState(false);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');

 useEffect(()=>onSnapshot(collection(db,'branches'),s=>{
  setBranches(s.docs.filter(d=>!d.data().archived).map(d=>({
   id:d.id,name:d.data().name||d.id
  })));
 },e=>setError(notificationError(e))),[]);

 useEffect(()=>onSnapshot(doc(db,'users',uid),s=>{
  setSaved(s.data()?.branchIds||[]);
  setLoaded(true);
 },e=>setError(notificationError(e))),[uid]);

 useEffect(()=>{
  if(!dirty)setSelected(saved);
 },[JSON.stringify(saved),dirty]);

 async function save(){
  setBusy(true);setError('');setNotice('');
  try{
   await saveOwnNotificationBranches(selected);
   setDirty(false);
   setNotice('負責據點已儲存，將同步更新所有已啟用裝置的候補提醒。');
  }catch(e){
   setError(notificationError(e));
  }finally{
   setBusy(false);
  }
 }

 return <fieldset className="notification-own-branches"
  disabled={!loaded||busy}>
  <legend>我負責的據點（候補通知）</legend>

  <p className="hint">
   只接收這些店的候補黃點與到期紅點；
   未選擇就不接收候補。查看全部據點的權限維持不變。
  </p>

  <p className="notification-owned-summary">
   目前負責據點：
   {saved.length
    ? saved.map(id=>branches.find(b=>b.id===id)?.name||id).join('、')
    : '尚未設定負責據點'}
  </p>

  <details>
   <summary>選擇負責據點 · 已選 {selected.length} 間</summary>
   <div>
    {branches.map(b=><label key={b.id}>
     <input type="checkbox" checked={selected.includes(b.id)}
      onChange={e=>{
       setDirty(true);setNotice('');
       setSelected(e.target.checked
        ? [...selected,b.id]
        : selected.filter(id=>id!==b.id));
      }}/>
     {b.name}
    </label>)}
   </div>
  </details>

  <button type="button" className="secondary"
   disabled={!dirty||busy} onClick={save}>
   {busy?'儲存中…':'儲存負責據點'}
  </button>

  {error&&<p role="alert">{error}</p>}
  {notice&&<p role="status">{notice}</p>}
 </fieldset>;
}
'''

changes['src/HeaderAlerts.tsx'] = r'''
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
'''

changes['src/use-initial-branch.ts'] = r'''
import {useEffect,useState} from 'react';

export default function useInitialBranch(
 uid:string|undefined,
 profile:any,
 branches:any[],
 setBranchId:(id:string)=>void
){
 const [initialized,setInitialized]=useState('');
 const scope=JSON.stringify(
  branches.filter(b=>!b.archived).map(b=>b.id)
 );

 useEffect(()=>{
  if(!uid){
   if(initialized)setInitialized('');
   return;
  }
  if(!profile||initialized===uid)return;

  const available=branches.filter(b=>!b.archived);
  if(!available.length)return;

  const own=(profile.branchIds||[])
   .map((id:string)=>available.find(b=>b.id===id))
   .find(Boolean);

  setBranchId((own||available[0]).id);
  setInitialized(uid);
 },[
  uid,profile?.role,JSON.stringify(profile?.branchIds),
  scope,initialized
 ]);

 return !!uid&&initialized===uid;
}
'''

changes['src/mobile-layout.css'] = r'''
/* Only phone layouts change. */
@media(max-width:760px){
 main > header {
  gap:8px;padding:10px 12px;min-height:60px;
 }
 main > header .breadcrumb {
  min-width:0;flex:1 1 auto;
 }
 main > header .breadcrumb strong {
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
 }
 main > header .header-right {gap:8px;flex:0 0 auto;}
 main > header .header-cheer {order:3;flex-basis:100%;}
 main > header .header-cheer:not(.has-text) {display:none;}

 .content {padding:20px 12px;}
 .page-title {
  align-items:stretch;flex-direction:column;
  gap:14px;margin-bottom:20px;
 }
 .page-title .filters {
  display:flex;flex-wrap:wrap;gap:8px;width:100%;
 }
 .page-title .filters > * {flex:1 1 135px;min-width:0;}

 .toolbar {flex-wrap:wrap;align-items:stretch;gap:10px;}
 .toolbar .search {flex:1 1 100%;min-width:0;}
 .toolbar .search .clearable-search {width:100%;max-width:none;}
 .toolbar > select {flex:1 1 140px;max-width:none;}
 .toolbar > .primary {margin-left:auto;}

 input:not([type=checkbox]):not([type=radio]),select,textarea {
  font-size:16px!important;
 }
 button.primary,button.secondary,.filters select,.filters input {
  min-height:44px;
 }
 .clear-search {min-width:36px;min-height:36px;}

 .cards {gap:10px;}
 .stat-card {min-width:0;padding:16px 12px;}
 .stat-card strong {font-size:28px;overflow-wrap:anywhere;}
 .table-wrap {
  max-width:100%;overscroll-behavior-x:contain;
  -webkit-overflow-scrolling:touch;
 }

 .modal-backdrop {
  padding:10px;
  padding-top:max(10px,env(safe-area-inset-top));
  padding-bottom:max(10px,env(safe-area-inset-bottom));
 }
 .modal-backdrop > .modal {
  width:100%;max-width:100%;padding:16px;
  max-height:calc(
   100dvh - 24px -
   env(safe-area-inset-top) - env(safe-area-inset-bottom)
  );
 }
 .modal-backdrop .modal {
  min-width:0!important;
  max-width:100%!important;
  width:min(100%,1100px)!important;
  max-height:calc(
   100dvh - 24px -
   env(safe-area-inset-top) - env(safe-area-inset-bottom)
  )!important;
  overflow-x:hidden;
 }
 .modal > .modal-heading {gap:10px;}
 .modal > .modal-heading h2 {font-size:18px;}
 .modal > .modal-heading > button {
  flex-basis:44px;width:44px;height:44px;
 }
 .modal form,.modal fieldset,.modal .table-wrap {
  min-width:0;max-width:100%;
 }
 .modal h2,.modal p,.modal label {overflow-wrap:anywhere;}
 .modal.wide.waiting-editor {width:100%;padding:16px;}

 .waiting-summary tr {padding:14px;gap:14px 12px;}
 .waiting-summary .waiting-name {font-size:16px;}
 .waiting-summary td:nth-child(2) {
  grid-column:1/-1;grid-row:1;
 }
 .waiting-detail-status .waiting-status-tabs {
  display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
 }
 .waiting-detail-status .waiting-status-tabs label {
  padding:10px 5px;white-space:normal;justify-content:flex-start;
 }
 .waiting-match-result {flex-wrap:wrap;}
 .waiting-contact-fields,.waiting-fields,.waiting-details {
  grid-template-columns:1fr;
 }

 .work-layout {
  grid-template-columns:minmax(0,1fr);
  grid-template-rows:minmax(150px,26dvh) minmax(440px,65dvh);
  height:auto;min-height:0;
 }
 .work-list {
  border-right:0;border-bottom:1px solid #dce5f1;padding:8px;
 }
 .work-task {padding:12px;}
 .work-detail,.work-messages {padding:14px;}
 .work-composer {padding:10px;}
 .work-composer textarea {min-height:76px;}
 .work-tabs {flex-wrap:wrap;}
 .work-filters > .clearable-search {
  flex:1 1 100%;max-width:none;
 }

 .notification-settings-button {width:40px;height:40px;}
 .notification-actions > button {flex:1 1 100%;}

 .sidebar {
  padding-bottom:max(20px,env(safe-area-inset-bottom));
  overflow-y:auto;
 }
 .mobile-sidebar-backdrop {
  display:block;position:fixed;inset:0;
  width:100%;height:100dvh;z-index:19;
  border-radius:0;background:#152e4d70;
 }
 .sidebar .mobile-sidebar-close {
  display:flex;align-self:flex-end;color:white;
  min-height:44px;margin-bottom:12px;padding:8px;
 }
 footer {
  padding-bottom:max(16px,env(safe-area-inset-bottom));
 }
}
'''

changes['src/notifications.css'] = r'''
.notification-settings-button {
 position:relative;align-items:center;padding:5px;display:none;
}
.notification-settings-button > span {
 position:absolute;top:-6px;right:-7px;min-width:16px;
 padding:1px 4px;border-radius:10px;background:#d42036;
 color:white;font-size:10px;line-height:14px;
}
.notification-modal p {line-height:1.7;}
.notification-state {
 padding:12px;background:#f3f6fb;border-radius:8px;
}
.notification-actions {
 display:flex;flex-wrap:wrap;gap:12px;margin-top:20px;
}
.notification-own-branches {
 margin:18px 0;padding:14px;min-width:0;
 border:1px solid #dce3eb;border-radius:8px;
}
.notification-own-branches details {
 margin:12px 0;border:1px solid #dce3eb;
 border-radius:8px;padding:10px;
}
.notification-own-branches summary {cursor:pointer;}
.notification-own-branches details > div {
 max-height:230px;overflow-y:auto;margin-top:10px;
}
.notification-own-branches label {
 display:flex;flex-direction:row;align-items:center;
 gap:10px;padding:8px 0;margin:0;
}
.notification-own-branches input[type=checkbox] {
 width:20px;height:20px;flex:0 0 20px;
}
.notification-inbox {
 margin-bottom:20px;padding-bottom:16px;
 border-bottom:1px solid #dce3eb;
}
.notification-inbox-row {
 display:flex;flex-direction:column;width:100%;
 align-items:flex-start;gap:6px;text-align:left;
 padding:14px 10px;border-bottom:1px solid #e6ebf1;
 border-radius:0;overflow-wrap:anywhere;
}
.notification-inbox-row span {font-size:13px;color:#647692;}
.notification-owned-summary {overflow-wrap:anywhere;}
.mobile-sidebar-close,.mobile-sidebar-backdrop {display:none;}
.personal-notification-settings {padding:22px;margin-bottom:20px;}
@media(max-width:760px){
 .notification-settings-button {display:inline-flex;}
}
'''

callable_code = r'''
export const pushOwnBranches=onCall(async request=>{
 const {uid}=await actor(request);
 originCheck(request);

 const raw=request.data?.branchIds;
 if(!Array.isArray(raw)||raw.length>100||
    raw.some(id=>typeof id!=='string'||!id||id.includes('/'))){
  throw new HttpsError('invalid-argument','據點選擇不正確');
 }

 const branchIds=[...new Set(raw)];

 await db.runTransaction(async tx=>{
  const profile=await tx.get(db.doc('users/'+uid));

  if(!['admin','supervisor'].includes(profile.data()?.role)){
   throw new HttpsError(
    'permission-denied',
    '只有主管與管理員可以設定自己的負責據點'
   );
  }

  for(const id of branchIds){
   const b=await tx.get(db.doc('branches/'+id));
   if(!b.exists||b.data().archived){
    throw new HttpsError(
     'failed-precondition','據點已停用或不存在，請重新選擇'
    );
   }
  }

  tx.update(profile.ref,{
   branchIds,updatedBy:uid,updatedAt:timestamp()
  });
 });

 await enqueueRegistered(uid);
 return {branchIds};
});
'''

manual_code = r'''
// mobile-notification-manual-v1
manualPages.find(p=>p.id==='notifications')?.topics.push({
 title:'鈴鐺未讀清單與自己的負責據點',
 steps:[
  '手機點頂端鈴鐺查看未讀待辦／候補及據點，點其中一筆跳到對應事項或候補明細並標記已讀；其它未讀保留，全部讀完清除鈴鐺數字。',
  '主管／管理員在電腦的「帳號與權限 → 我的負責據點」，或手機通知設定的「我負責的據點（候補通知）」查看目前負責的店，展開選擇並按「儲存負責據點」；未選擇顯示「尚未設定負責據點」，不接收候補提醒。',
  '負責據點設定跨裝置共用；不改變主管／管理員查看全部據點的權限，也不改變角色。店長仍以帳號指派據點為準。',
  '其他人在待辦或子項目新增訊息也會通知；自己的訊息不通知自己。同一份未讀待辦有多則新訊息仍只計一筆，讀完後再收到訊息會重新提醒。'
 ],
 result:'僅開啟鈴鐺不會把未看的提醒全部清除。背景通知仍須每台裝置各自啟用；未啟用背景推播也可使用網頁內未讀清單。'
});
manualPages.find(p=>p.id==='dashboard')?.topics.push({
 title:'手機使用與收合選單',
 steps:[
  '手機點左上角選單開啟藍色側欄，可按側欄「收合」或點外面遮罩關閉，不必先選頁面。',
  '手機篩選列會換行、表單改用較大的輸入字；待辦由左右雙欄改為上方清單、下方內容。',
  '彈出視窗限制在手機可視範圍內，內容在視窗內捲動，標題與關閉按鈕保持可見；寬表格可在自己的區域左右捲動。'
 ],
 result:'這些排版調整只套用手機寬度，不改變電腦版配置或資料。'
});
manualPages.find(p=>p.id==='users')?.topics.push({
 title:'我的負責據點與候補通知',
 steps:[
  '主管與管理員在「帳號與權限」上方「我的負責據點」查看目前負責的店；尚未設定會明確提示。',
  '展開「選擇負責據點」，勾選自己負責的分店後按「儲存負責據點」；只更新自己的負責據點，不改角色或查看全部據點的權限。',
  '候補配對與到期只通知這些店；待辦仍只通知明確指派給自己的事項。手機鈴鐺也能設定，電腦不顯示鈴鐺。'
 ],
 result:'設定與同帳號其它裝置同步；店長的所屬據點仍由主管／管理員指派。'
});
manualPages.find(p=>p.id==='dashboard')?.topics.push({
 title:'登入預設自己的據點',
 steps:[
  '店長登入後先顯示自己所屬的一間有效據點；主管／管理員優先顯示「我的負責據點」中的第一間。',
  '主管／管理員尚未設定負責據點時先顯示第一間可查看的有效據點；這不會自動把該店設為通知負責店。',
  '登入後仍可自行切換其它店或全部據點，頁面更新與即時資料不會一直把你切回預設店。'
 ],
 result:'不會擴大帳號據點權限；停用據點不作為預設。沒有可用據點時等待指派或新增據點。'
});
'''

def read(name):
    return (root/name).read_text(encoding='utf-8')

def replace_one(text, pattern, value, label):
    result, n = re.subn(pattern, lambda m: value, text, count=1)
    if n != 1:
        raise SystemExit('停止：找不到 '+label+'，尚未寫入。')
    return result

name = 'functions/notification-domain.js'
text = read(name)
text = re.sub(
    r"p\?\.role\s*===\s*['\"]manager['\"](?=\s*&&\s*intersects)",
    'enabled(p)', text
)
changes[name] = text

name = 'functions/notification-engine.js'
text = read(name)
text = re.sub(
    r"if\s*\(p\.role\s*!==\s*['\"]manager['\"]\)",
    "if(!enabled(p)||!(p.branchIds||[]).length)", text
)
changes[name] = text

name = 'functions/index.js'
text = read(name)
text = re.sub(
    r"p\?\.role\s*===\s*['\"]manager['\"]",
    '(enabled(p)&&(p.branchIds||[]).length>0)', text
)
if '// own-notification-branches-v1' in text:
    text = text.split('// own-notification-branches-v1')[0]
changes[name] = (
    text.rstrip()+'\n\n// own-notification-branches-v1\n'+callable_code
)

name = 'src/push-client.ts'
text = read(name)
if 'saveOwnNotificationBranches' not in text:
    text += (
        "\nexport const saveOwnNotificationBranches="
        "(branchIds:string[])=>rpc('pushOwnBranches',{branchIds});\n"
    )
changes[name] = text

name = 'src/main.tsx'
text = read(name)
text = re.sub(
    r'import\s+NotificationCenter\s+from\s+["\']'
    r'\./NotificationCenter["\'];?\s*',
    '', text
)

for component in ['HeaderAlerts', 'OwnNotificationBranches']:
    if 'import '+component+' ' not in text:
        text = (
            'import '+component+' from "./'+component+'";\n'+text
        )

if './mobile-layout.css' not in text:
    text = replace_one(
        text,
        r'import\s+["\']\./style\.css["\'];',
        'import "./style.css";\nimport "./mobile-layout.css";',
        'CSS import'
    )

if 'setWorkFocus' not in text:
    text = replace_one(
        text,
        r'function App\(\)\s*\{',
        'function App() {\n'
        ' const [workFocus,setWorkFocus]=useState<any>(null);',
        'App'
    )

if '<HeaderAlerts ' not in text:
    text = replace_one(
        text,
        r'<NotificationCenter\b[^>]*/>',
        '<HeaderAlerts uid={user.uid} branches={branches} '
        'profile={profile} work={work} waiting={waiting} '
        'onWaiting={(row:any)=>{setBranchId("all");'
        'setWaitingFocus(row.id);setPage("waiting");}} '
        'onWork={(task:any,thread:string)=>{setBranchId("all");'
        'setWorkFocus({id:task.id,thread,nonce:Date.now()});'
        'setPage("work");}}/>',
        '通知元件'
    )

if '<WorkTasks focus=' not in text:
    text = replace_one(
        text,
        r'<WorkTasks\s+profile=',
        '<WorkTasks focus={workFocus} '
        'onFocus={()=>setWorkFocus(null)} profile=',
        '待辦元件'
    )

if 'mobile-sidebar-backdrop' not in text:
    pattern = (
        r'<aside\s+className=\{mobile\s*\?\s*"sidebar open"'
        r'\s*:\s*"sidebar"\}>'
    )
    old = re.search(pattern, text)
    if not old:
        raise SystemExit('找不到側欄，尚未寫入。')
    text = replace_one(
        text, pattern,
        '{mobile&&<button className="mobile-sidebar-backdrop" '
        'aria-label="關閉側邊選單" onClick={()=>setMobile(false)}/>}'+
        old.group(0)+
        '<button type="button" className="mobile-sidebar-close" '
        'aria-label="收合選單" onClick={()=>setMobile(false)}>'
        '<X size={22}/>收合</button>',
        '手機側欄'
    )

if 'personal-notification-settings' not in text:
    pattern = (
        r'\{page\s*===\s*"users"\s*&&\s*global\s*&&\s*\(\s*<>'
    )
    old = re.search(pattern, text)
    if not old:
        raise SystemExit('找不到帳號頁，尚未寫入。')
    text = replace_one(
        text, pattern,
        old.group(0)+
        '<section className="panel personal-notification-settings">'
        '<h2>我的負責據點</h2>'
        '<OwnNotificationBranches uid={user.uid}/></section>',
        '我的負責據點'
    )

if 'import useInitialBranch ' not in text:
    text = 'import useInitialBranch from "./use-initial-branch";\n'+text

if 'const initialBranchReady=' not in text:
    text = replace_one(
        text,
        r'const branches = \[\.\.\.branchRows\]\.sort\(compareBranches\);',
        'const branches = [...branchRows].sort(compareBranches);\n'
        ' const initialBranchReady='
        'useInitialBranch(user?.uid,profile,branches,setBranchId);',
        '預設據點'
    )
    match = re.search(
        r'if\s*\(page\s*===\s*"cheers"\s*\|\|[^;]+return;', text
    )
    if not match:
        raise SystemExit('找不到資料載入設定，尚未寫入。')
    anchor = match.group(0)
    text = text.replace(
        anchor, anchor+'\n if(!initialBranchReady)return;', 1
    )
    start = text.index(anchor)
    dep = text.index('  }, [', start)
    text = (
        text[:dep]+
        text[dep:].replace('  }, [','  }, [initialBranchReady, ',1)
    )

text = text.replace(
    '指派據點（店長與員工適用）',
    '指派據點（主管／管理員的候補通知負責據點）'
)
changes[name] = text

name = 'src/WorkTasks.tsx'
text = read(name)

if 'focus,onFocus,profile' not in text:
    text = replace_one(
        text,
        r'export default function WorkTasks\(\{profile,',
        'export default function WorkTasks({focus,onFocus,profile,',
        '待辦 props'
    )

if 'focus?.nonce' not in text:
    pattern = r'const task=tasks\.find\(\(t:WorkRow\)=>t\.id===selected\);'
    old = re.search(pattern, text)
    if not old:
        raise SystemExit('找不到待辦選取狀態，尚未寫入。')

    effect = r'''
 useEffect(()=>{
  if(!focus)return;
  const target=tasks.find((t:WorkRow)=>t.id===focus.id);
  if(!target)return;
  setCategory('all');setSearch('');setPerson('');
  setOnlyUnread(false);setOnlyOverdue(false);
  setMode(target.deleted?'trash':target.done?'done':'open');
  setSelected(target.id);
  setThread(focus.thread||'main');
  onFocus?.();
 },[focus?.nonce,tasks]);
'''
    text = replace_one(
        text, pattern, old.group(0)+effect, '待辦跳轉'
    )

changes[name] = text

name = 'src/manual-content.ts'
text = read(name).replace(
    '主管與管理員只接收明確指派給自己的主事項或子項目所屬待辦，'
    '不計候補；只有查看權限但未被指派時不會收到通知。',
    '主管與管理員的待辦只接收明確指派給自己的主事項或子項目；'
    '候補則接收自己負責據點的配對黃點與到期紅點。'
    '只有查看全部據點的權限不會收到全部店候補。'
)
if '// mobile-notification-manual-v1' not in text:
    text += '\n'+manual_code
changes[name] = text

if (root/'PUSH_SETUP.md').exists():
    name = 'PUSH_SETUP.md'
    text = read(name)
    if 'mobile-notification-update-v1' not in text:
        text += (
            '\n\n<!-- mobile-notification-update-v1 -->\n'
            '主管與管理員也接收自己負責據點的候補配對及到期提醒。'
            '電腦到「帳號與權限 → 我的負責據點」設定；'
            '手機從鈴鐺設定。電腦不顯示鈴鐺。'
            '這次背景條件修改須重新部署 functions:notifications，'
            '不需重建金鑰。\n'
        )
    changes[name] = text

backup = root/'.update-backups'/(
    'mobile-notifications-'+
    datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
)

for name, text in changes.items():
    target = root/name
    if target.exists() and target.read_text(encoding='utf-8') == text:
        continue
    if target.exists():
        saved = backup/name
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_bytes(target.read_bytes())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8')

print(
    '手機排版、手機鈴鐺未讀清單、我的負責據點及操作手冊已更新；'
    '背景服務仍須重新部署。'
)
