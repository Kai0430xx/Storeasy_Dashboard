from pathlib import Path
import re, datetime

root = Path(__file__).resolve().parents[1]
changes = {}

detail_pairs = [
(
r"""useEffect(()=>{setItems([]);if(!selected||!task||task.deleted&&!global)return;return onSnapshot(collection(db,'workTasks',selected,'items'),s=>setItems(s.docs.map(d=>({id:d.id,...d.data()}))),e=>setError(workError(e)));},[selected,task?.deleted,global,reconnect]);""",
r"""useEffect(()=>{setItems([]);if(!selected||!task||task.deleted&&!global)return;let active=true;const unsubscribe=onSnapshot(collection(db,'workTasks',selected,'items'),s=>{if(active)setItems(s.docs.map(d=>({id:d.id,...d.data()})));},async e=>{if(!active)return;const ended=await workReadEnded(task,profile,e);if(!active)return;if(ended){setSelected('');setThread('main');}else setError(workError(e));});const stop=()=>{active=false;unsubscribe();};detailStops.current.add(stop);return()=>{stop();detailStops.current.delete(stop);};},[selected,task?.deleted,global,reconnect]);"""
),
(
r"""return onSnapshot(query(collection(db,'workTasks',selected,'threads',thread,'messages'),orderBy('createdAt','desc'),limit(messageLimit)),s=>{setMessages(s.docs.map(d=>({id:d.id,...d.data()})).reverse());setMore(s.docs.length===messageLimit);},e=>setError(workError(e)));""",
r"""let active=true;const unsubscribe=onSnapshot(query(collection(db,'workTasks',selected,'threads',thread,'messages'),orderBy('createdAt','desc'),limit(messageLimit)),s=>{if(active){setMessages(s.docs.map(d=>({id:d.id,...d.data()})).reverse());setMore(s.docs.length===messageLimit);}},async e=>{if(!active)return;const ended=await workReadEnded(task,profile,e,thread);if(!active)return;if(ended){if(thread==='main')setSelected('');setThread('main');}else setError(workError(e));});const stop=()=>{active=false;unsubscribe();};detailStops.current.add(stop);return()=>{stop();detailStops.current.delete(stop);};"""
),
(
r"""const action=(name:string,data:WorkRow={},target=thread)=>perform(()=>workAction(profile,selected,name,target,data));""",
r"""const action=(name:string,data:WorkRow={},target=thread)=>perform(async()=>{const id=selected,previousThread=thread;if(name==='delete'||name==='itemDelete'){stopDetails();if(name==='delete')setSelected('');setThread('main');}try{await workAction(profile,id,name,target,data);if(name==='itemDelete')setReconnect(n=>n+1);}catch(e){setSelected(id);setThread(previousThread);setReconnect(n=>n+1);throw e;}});"""
)
]

helpers = r'''
// work-delete-read-race-v1
export async function workReadEnded(
 task:WorkRow,profile:WorkRow,error:any,thread='main'
){
 if(!String(error?.code||'').includes('permission-denied')){
  return false;
 }

 try{
  const latest=await getDocFromServer(doc(db,'workTasks',task.id));
  if(!latest.exists()||latest.data().deleted||latest.data().purging){
   return true;
  }

  if(thread!=='main'){
   const item=await getDocFromServer(
    doc(db,'workTasks',task.id,'items',thread)
   );
   return !item.exists()||!!item.data().deleted;
  }
  return false;
 }catch{
  const uid=auth.currentUser?.uid;
  if(!uid||
     ['admin','supervisor'].includes(profile.role)||
     task.createdBy===uid||
     (task.branchIds||[]).some(
      (id:string)=>(profile.branchIds||[]).includes(id)
     )){
   return false;
  }

  try{
   const access=await getDocFromServer(
    doc(db,'workTaskAccess',uid+'_'+task.id)
   );
   return !access.exists()||!access.data().active;
  }catch{
   return false;
  }
 }
}

function useLiveNotificationThreads(
 tasks:WorkRow[],
 reads:Record<string,WorkRow>,
 uid:string|undefined,
 profile:WorkRow|null
):WorkRow[]{
 const [hidden,setHidden]=useState<Set<string>>(new Set());
 const key=JSON.stringify(
  tasks.map(t=>[t.id,t.revision,t.deleted,t.signals,reads[t.id]?.seen])
 );

 useEffect(()=>{
  let active=true;
  const candidates=tasks
   .filter(t=>!t.deleted&&!t.purging)
   .flatMap(task=>
    unreadThreads(task,reads[task.id],uid)
     .filter(thread=>thread!=='main')
     .map(thread=>({task,thread}))
   );

  void Promise.all(candidates.map(async({task,thread})=>{
   try{
    const s=await getDocFromServer(
     doc(db,'workTasks',task.id,'items',thread)
    );
    return !s.exists()||s.data().deleted
     ? task.id+':'+thread
     : null;
   }catch(e){
    return profile&&await workReadEnded(task,profile,e,thread)
     ? task.id+':'+thread
     : null;
   }
  })).then(keys=>{
   if(active){
    setHidden(new Set(keys.filter((k):k is string=>!!k)));
   }
  });

  return()=>{active=false;};
 },[key,uid,profile?.role,JSON.stringify(profile?.branchIds)]);

 return tasks.map(task=>({
  ...task,
  signals:Object.fromEntries(
   Object.entries(task.signals||{})
    .filter(([thread])=>!hidden.has(task.id+':'+thread))
  )
 }));
}
'''

child_filter = r'''
const live=[...map.values()]
 .filter(t=>!t.deleted&&!t.purging)
 .map(t=>({...t,signals:{...t.signals}}));

const children=live.flatMap(task=>
 Object.keys(task.signals||{})
  .filter(thread=>
   thread!=='main'&&
   workUnread(
    [{...task,signals:{[thread]:task.signals[thread]}}],
    reads,uid
   ).count>0
  )
  .map(thread=>({task,thread}))
);

for(const group of chunks(children,100)){
 const snapshots=await db.getAll(
  ...group.map(({task,thread})=>
   db.doc(`workTasks/${task.id}/items/${thread}`)
  )
 );
 snapshots.forEach((s,i)=>{
  if(!s.exists||s.data().deleted){
   delete group[i].task.signals[group[i].thread];
  }
 });
}
return workUnread(live,reads,uid);
'''

work_handler = r'''
export const notifyWork=onDocumentWritten(
 'workTasks/{id}',async e=>{
  const rows=beforeAfter(e);
  const assigned=docs(
   await db.collection('workTaskAccess')
    .where('taskId','==',e.params.id).get()
  ).filter(a=>a.active).map(a=>a.uid);

  const after=e.data?.after.data();
  const log=after?.lastActionId
   ? (await db.doc(
      `workTasks/${e.params.id}/history/${after.lastActionId}`
     ).get()).data()
   : null;

  await audience(
   (uid,p)=>rows.some(r=>
    workNotificationVisible(r,uid,p,assigned.includes(uid))
   ),
   {
    work:true,
    notify:!!after&&!after.deleted&&!after.purging&&
     !['delete','itemDelete','messageDelete'].includes(log?.action)
   }
  );
 }
);
'''

access_handler = r'''
export const notifyWorkAccess=onDocumentWritten(
 'workTaskAccess/{id}',async e=>{
  const before=e.data?.before.data();
  const after=e.data?.after.data();
  const notify=!!after?.active&&
   (after.sources||[]).some(
    source=>!(before?.sources||[]).includes(source)
   );

  for(const uid of new Set(beforeAfter(e).map(d=>d.uid))){
   if(uid)await enqueueRegistered(uid,{work:true,notify});
  }
 }
);
'''

waiting_handler = r'''
export const notifyWaiting=onDocumentWritten(
 'waitingList/{id}',async e=>{
  const rows=beforeAfter(e);
  const after=e.data?.after.data();

  await audience(
   (uid,p)=>rows.some(r=>waitingNotificationVisible(r,uid,p)),
   {
    waiting:true,
    notify:!!after&&!after.deleting&&
     ['waiting','contacted','visit'].includes(after.status)
   }
  );
 }
);
'''

manual = r'''
// unread-live-notifications-manual-v1
manualPages.find(p=>p.id==='notifications')?.topics.push({
 title:'只保留未讀且未刪除的提醒',
 steps:[
  '手機鈴鐺只列出未讀的有效待辦及候補；已讀後自動移除，不保留已讀通知清單。',
  '移到垃圾桶、永久刪除的主事項與已刪除子項目不再列入手機提醒或未讀筆數；刪除動作本身不產生新的待辦提醒。',
  '店長刪除主事項或子項目前，頁面會先結束該內容的即時連線；刪除成功返回清單或主事項，無須重新連線後再刪一次。'
 ],
 result:'仍保留真正的權限及儲存失敗訊息；不會為了隱藏錯誤而放寬資料存取權限。'
});

manualPages.find(p=>p.id==='notifications')?.topics.push({
 title:'已讀與刪除採靜音同步',
 steps:[
  '新未讀事項或他人新增訊息才作為新的提醒；已讀、消除未讀及刪除不作為新的提醒。',
  '為了保留 App 關閉時的圖示數字同步，已讀與刪除會傳送靜音推播更新剩餘筆數。',
  'iPhone 系統仍可能顯示更新後的通知卡片，無法保證完全不顯示卡片；網頁內鈴鐺不保留已讀及已刪除項目。'
 ],
 result:'保留同帳號背景數字同步及 4→3→0 行為；不發出新的聲音提醒。'
});
'''

def read(name):
    return (root/name).read_text(encoding='utf-8')

def swap(text, old, new, label):
    if old in text:
        return text.replace(old, new)
    if new in text:
        return text
    raise SystemExit('停止：找不到 '+label+'，尚未寫入。')

name = 'src/work-tasks.ts'
text = read(name)

if 'getDocFromServer}' not in text:
    text = swap(
        text,
        'limit,getDocs}',
        'limit,getDocs,getDocFromServer}',
        'Firestore import'
    )

anchor = (
    'export function unreadThreads('
    'task:WorkRow,receipt?:WorkRow,uid=auth.currentUser?.uid){'
)
if 'if(task.deleted||task.purging)return [];' not in text:
    text = swap(
        text, anchor,
        anchor+'\n if(task.deleted||task.purging)return [];',
        '未讀判斷'
    )

text = swap(
    text,
    'e=>{assigned.delete(id);publish();setError(workError(e));}',
    'e=>{const previous=assigned.get(id)||{id};'
    'assigned.delete(id);publish();'
    'void workReadEnded(previous,profile,e).then(ended=>{'
    'if(!ended)setError(workError(e));});}',
    '被指派事項連線'
)

text = swap(
    text,
    'return {tasks,reads,error,retry:',
    'const notificationTasks='
    'useLiveNotificationThreads(tasks,reads,uid,profile);\n'
    ' return {tasks:notificationTasks,reads,error,retry:',
    '有效子項目通知'
)

if '// work-delete-read-race-v1' not in text:
    text += helpers
changes[name] = text

name = 'src/WorkTasks.tsx'
text = read(name)

text = swap(
    text,
    'markWorkRead,unreadThreads,stamp,workError',
    'markWorkRead,unreadThreads,stamp,workReadEnded,workError',
    '錯誤確認 helper'
)

if 'const detailStops=' not in text:
    anchor = 'const notificationBox=useRef<HTMLDetailsElement>(null);'
    text = swap(
        text, anchor,
        anchor+
        '\n const detailStops=useRef(new Set<()=>void>());'
        '\n const stopDetails=()=>{'
        'for(const stop of detailStops.current)stop();'
        'detailStops.current.clear();};',
        '內容連線管理'
    )

for old, new in detail_pairs:
    text = swap(text, old, new, '刪除時結束舊連線')

text = text.replace(
    'markWorkRead(task,thread).catch(e=>setError(workError(e)))',
    'markWorkRead(task,thread).catch(async e=>{'
    'if(!await workReadEnded(task,profile,e,thread))'
    'setError(workError(e));})'
)

text = text.replace(
    '{items.map(i=><button key={i.id}',
    '{items.filter(i=>!i.deleted||(global&&task?.deleted))'
    '.map(i=><button key={i.id}'
)
changes[name] = text

name = 'functions/notification-domain.js'
text = read(name)
if 'if(task.deleted||task.purging)continue;' not in text:
    text, n = re.subn(
        r'for\s*\(const task of tasks\)\{',
        lambda m: m[0]+'\n  if(task.deleted||task.purging)continue;',
        text,
        count=1
    )
    if n != 1:
        raise SystemExit('找不到背景未讀計算，尚未寫入。')
changes[name] = text

name = 'functions/notification-engine.js'
text = read(name)
if 'return workUnread(live,reads,uid);' not in text:
    text = swap(
        text,
        'return workUnread([...map.values()],reads,uid);',
        child_filter,
        '背景排除刪除子項目'
    )

if 'silent:!q.notify' not in text:
    text, n = re.subn(
        r'count:state\.count,\s*enabled:active,',
        lambda m: m[0]+'silent:!q.notify,',
        text,
        count=1
    )
    if n != 1:
        raise SystemExit('找不到推播內容，尚未寫入。')
changes[name] = text

name = 'functions/index.js'
text = read(name)
for start, end, handler in [
    ('export const notifyWork=',
     'export const notifyWorkAccess=', work_handler),
    ('export const notifyWorkAccess=',
     'export const notifyWorkRead=', access_handler),
    ('export const notifyWaiting=',
     'export const notifyWaitingRead=', waiting_handler)
]:
    a = text.index(start)
    b = text.index(end, a)
    text = text[:a]+handler+text[b:]

text = re.sub(
    r'\{waiting:true\}\s*,\s*Date\.parse',
    '{waiting:true,notify:true},Date.parse',
    text
)

a = text.index('export const pushExpiryTick=')
b = text.find('// own-notification-branches-v1', a)
if b < 0:
    b = len(text)

part = re.sub(
    r'\{waiting:true\}',
    '{waiting:true,notify:true}',
    text[a:b]
)
text = text[:a]+part+text[b:]
changes[name] = text

name = 'public/sw.js'
text = read(name)
if 'incoming.silent===true' not in text:
    text = swap(
        text,
        'silent:incoming.version',
        'silent:incoming.silent===true||incoming.version',
        '靜音推播'
    )
changes[name] = text

name = 'src/manual-content.ts'
text = read(name)
if '// unread-live-notifications-manual-v1' not in text:
    text += manual
changes[name] = text

backup = root/'.update-backups'/(
    'fix-work-delete-'+
    datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
)

for name, text in changes.items():
    target = root/name
    if target.read_text(encoding='utf-8') == text:
        continue
    saved = backup/name
    saved.parent.mkdir(parents=True, exist_ok=True)
    saved.write_bytes(target.read_bytes())
    target.write_text(text, encoding='utf-8')

print(
    '待辦刪除連線、未讀清單及靜音同步已修正；'
    '背景服務仍需重新部署。'
)
