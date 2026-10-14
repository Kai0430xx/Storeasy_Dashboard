from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MARK = 'storeasy-work-team-v1'
prepared = {}


def change(name, pairs):
    path = ROOT / name
    text = path.read_text(encoding='utf-8')
    if MARK in text:
        return
    edits = []
    for old, new in pairs:
        if text.count(old) != 1:
            raise RuntimeError(
                '版本不符，未寫入任何檔案：' + name + ' / ' + old[:70]
            )
        pos = text.index(old)
        edits.append((pos, pos + len(old), new))
    edits.sort()
    if any(
        edits[i][1] > edits[i + 1][0]
        for i in range(len(edits) - 1)
    ):
        raise RuntimeError('更新區塊重疊：' + name)
    for start, end, value in reversed(edits):
        text = text[:start] + value + text[end:]
    prepared[name] = text


change('src/WorkTasks.tsx', [
    (
        'import React,{useEffect,useRef,useState} from',
        'import {useWorkPeople} from "./work-people";\nimport React,{useEffect,useRef,useState} from'
    ),
    (
        "st empty={title:'',description:'',assignee:'',due:'',priority:'normal'};\nfunction Dialog({",
        "st empty={title:'',description:'',assignee:'',directAssigneeIds:[],due:'',priority:'normal'};\nfunction Dialog({"
    ),
    (
        '/div></div>;}\nfunction Fields({value,onChange}:any){return <><label>標題<input required maxL',
        '/div></div>;}\nfunction Fields({value,onChange,people}:any){return <><label>標題<input required maxL'
    ),
    (
        'ue})}/></label><div className="work-fields"><label>負責人（選填）<input maxLength={80} value={value.assignee} onChange={e=>onChange({...value,assignee:e.target.value})}/></label><label>預計完成日（選填）<input type="date" value={va',
        'ue})}/></label><div className="work-fields"><div className="work-assignee-field"><div>指派對象（選填，可多選）</div><details className="work-assignee-picker"><summary>{value.directAssigneeIds?.length?`已指派 ${value.directAssigneeIds.length} 人`:\'不指定\'}</summary><button type="button" className="text-button" onClick={()=>onChange({...value,assignee:\'\',directAssigneeIds:[]})}>不指定／清除選擇</button><div className="work-assignee-options">{people.map((p:WorkRow)=><label key={p.id}><input type="checkbox" checked={(value.directAssigneeIds||[]).includes(p.id)} onChange={e=>onChange({...value,assignee:\'\',directAssigneeIds:e.target.checked?[...(value.directAssigneeIds||[]),p.id]:(value.directAssigneeIds||[]).filter((id:string)=>id!==p.id)})}/><span>{p.username}</span></label>)}</div></details></div><label>預計完成日（選填）<input type="date" value={va'
    ),
    (
        "es,branchId,tasks,reads,error:loadError,retry}:any){\n const global=['admin','supervisor'].includes(profile.role),uid=auth.currentUser?.uid;\n const [selected,setSelected]=useState(''),",
        "es,branchId,tasks,reads,error:loadError,retry,peopleUsers=[],onSelectBranch}:any){\n const global=['admin','supervisor'].includes(profile.role),uid=auth.currentUser?.uid;\n const people=useWorkPeople(profile,peopleUsers);\n const [selected,setSelected]=useState(''),"
    ),
    (
        '[reconnect,setReconnect]=useState(0);\n const historyCursor=useRef<any>(null);const [histor',
        '[reconnect,setReconnect]=useState(0);\n const notificationBox=useRef<HTMLDetailsElement>(null);\n const historyCursor=useRef<any>(null);const [histor'
    ),
    (
        'false);const end=useRef<HTMLDivElement>(null);\n const task=tasks.find((t:WorkRow)=>t.id===',
        "false);const end=useRef<HTMLDivElement>(null);\n const assignedNames=(node:WorkRow)=>{const names=(node.directAssigneeIds||[]).map((id:string)=>people.options.find(p=>p.id===id)?.username||'已停用帳號');return names.length?names.join('、'):node.assignee||'';};\n const task=tasks.find((t:WorkRow)=>t.id==="
    ),
    (
        "t.description}`.includes(search))&&(!person||(t.assignee||'').includes(person))&&(!onlyUnread||unreadThreads(t,reads[t.id]",
        "t.description}`.includes(search))&&(!person||[...(t.directAssigneeIds||[]).map((id:string)=>people.options.find(p=>p.id===id)?.username||''),t.assignee||''].some(name=>name.includes(person)))&&(!onlyUnread||unreadThreads(t,reads[t.id]"
    ),
    (
        'ad=task?unreadThreads(task,reads[task.id]):[];\n const inactive=!task||task.deleted||item?.',
        "ad=task?unreadThreads(task,reads[task.id]):[];\n const notices=tasks.flatMap((t:WorkRow)=>unreadThreads(t,reads[t.id]).filter(thread=>!t.deleted||thread==='main').map(thread=>({task:t,thread,time:Math.max(0,...Object.entries(t.signals?.[thread]||{}).filter(([actor])=>actor!==uid).map(([,v])=>stamp(v)))}))).sort((a:any,b:any)=>b.time-a.time);\n const inactive=!task||task.deleted||item?."
    ),
    (
        "g)=>{setForm(kind==='edit'?{...empty,...item,expected:Object.fromEntries(Object.keys(empty",
        "g)=>{setForm(kind==='edit'?{...empty,...item,directAssigneeIds:item.directAssigneeIds||people.options.filter(p=>p.username===item.assignee).map(p=>p.id),expected:Object.fromEntries(Object.keys(empty"
    ),
    (
        ';\n return <section className="work-area">\n  {(error||loadError)&&<div className="alert err',
        ';\n return <section className="work-area">\n  {people.error&&<div className="alert error" role="alert">{people.error}</div>}{(error||loadError)&&<div className="alert err'
    ),
    (
        '="alert success" role="status">{notice}</div>}{tasks.filter((t:WorkRow)=>t.deleted&&unreadThreads(t,reads[t.id]).includes(\'main\')).map((t:WorkRow)=><div className="alert" key={t.id}>{dot}「{t.title}」已移到垃圾桶 <button disabled={busy} onClick={()=>perform(()=>markWorkRead(t,\'main\'))}>已讀</button></div>)}\n  <div className="work-toolbar"><div classN',
        '="alert success" role="status">{notice}</div>}\n  <div className="work-toolbar"><div classN'
    ),
    (
        'ed||thread===\'main\'))&&dot}</button>)}</div><button className="work-add" onClick={()=>{set',
        'ed||thread===\'main\'))&&dot}</button>)}</div><div className="work-toolbar-right"><details className="work-notifications" ref={notificationBox}><summary>{notices.length>0&&dot}通知{notices.length>0&&<span className="work-notice-count">{notices.length}</span>}</summary><div className="work-notice-panel"><strong>未讀通知</strong>{!notices.length&&<p>目前沒有未讀通知。</p>}{notices.map((notice:any)=><button type="button" key={`${notice.task.id}:${notice.thread}`} className="work-notice-row" disabled={busy} onClick={()=>{if(notificationBox.current)notificationBox.current.open=false;if(notice.task.deleted){perform(()=>markWorkRead(notice.task,\'main\'));return;}onSelectBranch?.(\'all\');setMode(notice.task.done?\'done\':\'open\');choose(notice.task.id,notice.thread);}}><strong className={notice.task.priority===\'urgent\'?\'work-urgent-title\':\'\'}>{notice.task.title}</strong><small>{notice.task.deleted?\'已移到垃圾桶 · 點此標記已讀\':notice.thread===\'main\'?\'事項有更新\':`${selected===notice.task.id?items.find(i=>i.id===notice.thread)?.title||\'子項目\':\'子項目\'}有更新`} · {new Intl.DateTimeFormat(\'zh-TW\',{timeZone:\'Asia/Taipei\',month:\'2-digit\',day:\'2-digit\',hour:\'2-digit\',minute:\'2-digit\'}).format(new Date(notice.time))}</small></button>)}</div></details><button className="work-add" onClick={()=>{set'
    ),
    (
        'log({kind:\'create\'});}}>＋ 新增事項</button></div>\n  <div className="work-filters"><input aria-',
        'log({kind:\'create\'});}}>＋ 新增事項</button></div></div>\n  <div className="work-filters"><input aria-'
    ),
    (
        'tSearch(e.target.value)}/><input aria-label="篩選負責人" placeholder="負責人" value={person} onChange={e=>setPerson(e.tar',
        'tSearch(e.target.value)}/><input aria-label="搜尋指派對象" placeholder="指派對象" value={person} onChange={e=>setPerson(e.tar'
    ),
    (
        "ted':''}`} onClick={()=>choose(t.id)}><strong>{t.title}</strong>{red.length>0&&dot}<small>{Object.values(t.branchNames).join('、')}{t.mode==='shared'?' · 共同協作':''}</small><small>{t.priority==='urgent'?'緊急 · ':''}{t.assignee?`${t.assignee} · `:''}{t.due?`${t.due}${!t.done&&t.due<day()?' 已逾期':''}`:''}{t.done?'已完成':''}</small></button>\n   {selected===t.id&&<div className",
        'ted\' :\'\'}`} onClick={()=>choose(t.id)}><strong className={t.priority===\'urgent\'?\'work-urgent-title\':\'\'}>{t.title}</strong>{red.length>0&&dot}<small className="work-task-meta"><span>{t.branchIds.length>1?`共同協作 · 參與 ${t.branchIds.length} 間據點`:(t.branchNames?.[t.branchIds[0]]||\'未命名據點\')}</span>{assignedNames(t)&&<span title={assignedNames(t)}>· {assignedNames(t)}</span>}</small>{(t.due||t.done)&&<small>{t.due?`${t.due}${!t.done&&t.due<day()?\' 已逾期\':\'\'}`:\'\'}{t.done?\'已完成\':\'\'}</small>}</button>\n   {selected===t.id&&<div className'
    ),
    (
        "id,i.id)}>{i.deleted?'已刪除 · ':i.done?'✓ ':''}{i.title}{red.includes(i.id)&&dot}</button>)}{!t.delet",
        "id,i.id)}>{i.deleted?'已刪除 · ':i.done?'✓ ':''}<span className={i.priority==='urgent'?'work-urgent-title':''}>{i.title}</span>{red.includes(i.id)&&dot}</button>)}{!t.delet"
    ),
    (
        'ork-detail"><div className="work-toolbar"><h2>{item.title}</h2>{!inactive&&<label classNam',
        'ork-detail"><div className="work-toolbar"><h2 className={item.priority===\'urgent\'?\'work-urgent-title\':\'\'}>{item.title}</h2>{!inactive&&<label classNam'
    ),
    (
        'ame="work-description">{item.description}</p><div className="work-meta">{item.assignee&&<span>負責人：{item.assignee}</span>}{item.due&&<span>預計完成：{item.due}</span>}{item.priority===\'urgent\'&&<span className="danger">緊急</span>}<span>建立者：{item.createdName}</span>{i',
        'ame="work-description">{item.description}</p>{task.branchIds.length>1&&<details className="work-participants" key={`${task.id}:${thread}`}><summary>查看參與據點（{task.branchIds.length} 間）</summary><ul>{task.branchIds.map((id:string)=><li key={id}>{task.branchNames?.[id]||\'未命名據點\'}</li>)}</ul></details>}<div className="work-meta">{assignedNames(item)&&<span>指派對象：{assignedNames(item)}</span>}{item.due&&<span>預計完成：{item.due}</span>}<span>建立者：{item.createdName}</span>{i'
    ),
    (
        'ick={()=>{setThread(i.id);setDialog(null);}}>{i.title} · 查看內容</button><button disabled={busy} onCli',
        "ick={()=>{setThread(i.id);setDialog(null);}}><span className={i.priority==='urgent'?'work-urgent-title':''}>{i.title}</span> · 查看內容</button><button disabled={busy} onCli"
    ),
    (
        'abel>:<Fields value={form} onChange={setForm}/>}\n    {error&&<div className="alert error">',
        'abel>:<Fields value={form} onChange={setForm} people={people.options}/>}\n    {error&&<div className="alert error">'
    ),
    (
        '</Dialog>}\n </section>;\n}\n\n// storeasy-work-polish-v1\n\n// storeasy-work-reconnect-v1\n',
        '</Dialog>}\n </section>;\n}\n\n// storeasy-work-participants-v1\n\n// storeasy-work-urgent-title-v1\n\n// storeasy-work-inline-meta-v1\n'
    ),
])

change('src/work-tasks.ts', [
    (
        "敗');\n if(isWorkQuota(error))return `Firebase 回傳額度限制（${code}）：${message}。請按「重新連線」重試。`;\n if(code.includes('permission'))return `操",
        "敗');\n if(isWorkQuota(error))return `Firebase 仍回傳額度限制（${code}）：${message}。若已升級，請按「重新連線」重試；這段提示不代表目前一定是免費方案。`;\n if(code.includes('permission'))return `操"
    ),
    (
        "ins-any',profile.branchIds.slice(i,i+30))));\n  scopes.forEach((q,i)=>stops.push(onSnapshot",
        "ins-any',profile.branchIds.slice(i,i+30))));\n\n  scopes.forEach((q,i)=>stops.push(onSnapshot"
    ),
    (
        'Tasks([...new Map([...parts.values()].flat().map(t=>[t.id,t])).values()]);},(e:any)=>setError(workError(e)))));\n  stops.push(onSnapshot(query(collection(db,',
        "Tasks([...new Map([...parts.values()].flat().concat([...((parts as any).assigned?.values()||[])]).map(t=>[t.id,t])).values()]);},(e:any)=>setError(workError(e)))));\n  if(profile.role==='manager'){\n   const assigned=new Map<string,WorkRow>(),watchers=new Map<string,()=>void>();\n   const publish=()=>setTasks([...new Map([...parts.values()].flat().concat([...assigned.values()]).map(t=>[t.id,t])).values()]);\n   stops.push(onSnapshot(query(collection(db,'workTaskAccess'),where('uid','==',uid)),snapshot=>{\n    const active=new Set(snapshot.docs.filter(d=>d.data().active).map(d=>String(d.data().taskId)));\n    for(const [id,stop] of watchers)if(!active.has(id)){stop();watchers.delete(id);assigned.delete(id);}\n    for(const id of active)if(!watchers.has(id))watchers.set(id,onSnapshot(doc(db,'workTasks',id),snapshot=>{if(snapshot.exists())assigned.set(id,{id,...snapshot.data()});else assigned.delete(id);publish();},e=>{assigned.delete(id);publish();setError(workError(e));}));\n    publish();\n   },e=>setError(workError(e))));\n   stops.push(()=>watchers.forEach(stop=>stop()));\n   (parts as any).assigned=assigned;\n  }\n  stops.push(onSnapshot(query(collection(db,"
    ),
    (
        ",assignee:String(input.assignee||'').trim(),due:input.due||'',priority:input.priority||'no",
        ",assignee:String(input.assignee||'').trim(),directAssigneeIds:[...new Set<string>(input.directAssigneeIds||[])].sort(),due:input.due||'',priority:input.priority||'no"
    ),
    (
        "0)throw new Error('標題須為1～120字');\n if(result.description.length>5000||result.assignee.lengt",
        "0)throw new Error('標題須為1～120字');\n if(result.directAssigneeIds.length>100||result.directAssigneeIds.some(id=>typeof id!=='string'||!id||id.includes('/')))throw new Error('指派對象不合法或超過100人');\n if(result.description.length>5000||result.assignee.lengt"
    ),
    (
        "w Error('內容最多5000字，負責人最多80字');\n return result;\n}\nexport async function createWorkTasks(pro",
        "w Error('內容最多5000字，負責人最多80字');\n return result;\n}\nasync function assignmentWrites(tx:any,taskId:string,thread:string,before:any,after:any,actionId:string,actorUid:string){\n const oldIds=new Set<string>(before&&!before.deleted?before.directAssigneeIds||[]:[]);\n const newIds=new Set<string>(after&&!after.deleted?after.directAssigneeIds||[]:[]);\n const changed=[...new Set([...oldIds,...newIds])].filter(uid=>oldIds.has(uid)!==newIds.has(uid));\n const writes:any[]=[];\n for(const uid of changed){\n  const ref=doc(db,'workTaskAccess',`${uid}_${taskId}`),snapshot=await tx.get(ref);\n  const oldSources:string[]=snapshot.data()?.sources||[];\n  const sources=newIds.has(uid)?[...new Set([...oldSources,thread])]:oldSources.filter(source=>source!==thread);\n  writes.push([ref,{uid,taskId,sources,primaryThread:sources[0]||'',active:sources.length>0,updatedBy:actorUid,updatedAt:serverTimestamp(),lastActionId:actionId}]);\n }\n return writes;\n}\nexport async function createWorkTasks(pro"
    ),
    (
        "}};\n  await runTransaction(db,async tx=>{\n   tx.set(ref,entry);\n   tx.set(audit,{action:'create',thread:'m",
        "}};\n  await runTransaction(db,async tx=>{\n   const access=await assignmentWrites(tx,ref.id,'main',null,entry,audit.id,who.uid);\n   tx.set(ref,entry);\n   for(const [target,value] of access)tx.set(target,value);\n   tx.set(audit,{action:'create',thread:'m"
    ),
    (
        "temRestore')throw new Error('子項目已刪除或不存在');\n  let patch:WorkRow={},before:any=null,after:an",
        "temRestore')throw new Error('子項目已刪除或不存在');\n  const pending:any[]=[];\n  let patch:WorkRow={},before:any=null,after:an"
    ),
    (
        "xpected&&Object.keys(input.expected).some(k=>input.expected[k]!==target?.[k]))throw new Error('內容已被其他人修改，請關閉視窗後重新開啟。');before=target;after={...target,...updated};\n   if(item)tx.set(item,after);else patch=updated;\n  }else if(action==='co",
        "xpected&&Object.keys(input.expected).some(k=>JSON.stringify(input.expected[k]??null)!==JSON.stringify(target?.[k]??null)))throw new Error('內容已被其他人修改，請關閉視窗後重新開啟。');before=target;after={...target,...updated};\n   if(item)pending.push([item,after]);else patch=updated;\n  }else if(action==='co"
    ),
    (
        ';after={...target,...completed};\n   if(item){tx.set(item,after);patch.openChildren=r.openChildren+(input.do',
        ';after={...target,...completed};\n   if(item){pending.push([item,after]);patch.openChildren=r.openChildren+(input.do'
    ),
    (
        'ull,completedName:null,completedAt:null};\n   tx.set(newItem,after);patch={childCount:r.childCount+1,openChildr',
        'ull,completedName:null,completedAt:null};\n   pending.push([newItem,after]);patch={childCount:r.childCount+1,openChildr'
    ),
    (
        ';\n   before=target;after={...target,deleted};tx.set(item,after);\n   patch={openChildren:r.openChildren+(tar',
        ';\n   before=target;after={...target,deleted};pending.push([item,after]);\n   patch={openChildren:r.openChildren+(tar'
    ),
    (
        "erverTimestamp(),edited:false,deleted:false};tx.set(message,after);\n  }else if(action==='messageEdit'||action=",
        "erverTimestamp(),edited:false,deleted:false};pending.push([message,after]);\n  }else if(action==='messageEdit'||action="
    ),
    (
        "eleted:true,deletedAt:serverTimestamp()};\n   tx.set(message,after);\n  }else throw new Error('不支援此操作');\n  const",
        "eleted:true,deletedAt:serverTimestamp()};\n   pending.push([message,after]);\n  }else throw new Error('不支援此操作');\n  const"
    ),
    (
        'read],[who.uid]:serverTimestamp()}};\n  const updated={...r,...patch,signals,revision:r.rev',
        "read],[who.uid]:serverTimestamp()}};\n  const access=['edit','addItem','itemDelete','itemRestore'].includes(action)?await assignmentWrites(tx,taskId,eventThread,before,after,audit.id,who.uid):[];\n  const updated={...r,...patch,signals,revision:r.rev"
    ),
    (
        "edAt:serverTimestamp(),lastActionId:audit.id};\n  if(eventThread==='main'&&!action.startsWi",
        "edAt:serverTimestamp(),lastActionId:audit.id};\n  for(const [target,value] of [...pending,...access])tx.set(target,value);\n  if(eventThread==='main'&&!action.startsWi"
    ),
    (
        '0)))).docs.map(d=>({id:d.id,...d.data()}));}\n\n// storeasy-work-polish-v1\n\n// storeasy-work-reconnect-v1\n',
        '0)))).docs.map(d=>({id:d.id,...d.data()}));}\n'
    ),
])

CSS = """
/* storeasy-work-participants-v1 */
.work-participants{margin:10px 0;font-size:13px;color:#526a8c}
.work-participants summary{cursor:pointer;width:fit-content;color:#173f75;padding:5px 0}
.work-participants summary:focus-visible{outline:2px solid #173f75;outline-offset:3px}
.work-participants ul{display:flex;flex-wrap:wrap;gap:8px;list-style:none;padding:0;margin:8px 0;max-height:150px;overflow:auto}
.work-participants li{background:#f0f4fa;border:1px solid #e0e7f1;border-radius:6px;padding:5px 9px;overflow-wrap:anywhere}

/* storeasy-work-urgent-title-v1 */
.work-area .work-urgent-title,.work-area .work-task .work-urgent-title{color:#b91c1c}

/* storeasy-work-inline-meta-v1 */
.work-task .work-task-meta{display:flex;align-items:center;gap:6px;flex-wrap:nowrap}
.work-task-meta span{min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

/* storeasy-work-assignees-v1 */
.work-assignee-field{margin-bottom:12px}
.work-assignee-picker{margin-top:8px;border:1px solid #dce3eb;border-radius:7px;padding:10px 12px;background:#fff}
.work-assignee-picker summary{cursor:pointer;color:#173f75}
.work-assignee-options{max-height:240px;overflow:auto;margin-top:8px}
.modal.work-dialog .work-assignee-options label{display:flex;flex-direction:row;align-items:center;gap:10px;margin:0;padding:9px 0}
.modal.work-dialog .work-assignee-options input{width:18px;min-width:18px;height:18px;flex:0 0 18px;padding:0;margin:0;accent-color:#173f75}

/* storeasy-work-notifications-v1 */
.work-toolbar-right{display:flex;align-items:center;gap:10px}
.work-notifications{position:relative}
.work-notifications>summary{cursor:pointer;display:flex;align-items:center;gap:7px;border:1px solid #dce5f1;border-radius:8px;background:#fff;padding:9px 12px;list-style:none;font-size:13px}
.work-notifications>summary::-webkit-details-marker{display:none}
.work-notifications .work-dot{margin:0}
.work-notice-count{background:#eaf0fb;color:#173f75;border-radius:12px;padding:1px 6px;font-size:12px}
.work-notice-panel{position:absolute;right:0;top:calc(100% + 8px);width:min(350px,calc(100vw - 40px));max-height:360px;overflow:auto;z-index:12;background:#fff;border:1px solid #dce5f1;border-radius:10px;box-shadow:0 10px 30px #173f7520;padding:14px}
.work-notice-panel>strong{font-size:14px}
.work-notice-panel>p{font-size:13px;color:#647692}
.work-notice-row{display:block;width:100%;text-align:left;padding:12px 0;border-radius:0;border-bottom:1px solid #e8edf5}
.work-notice-row:last-child{border-bottom:0}
.work-notice-row>strong{display:block;overflow-wrap:anywhere;font-size:13px}
.work-notice-row>small{display:block;color:#647692;font-size:12px;margin-top:5px;line-height:1.6}
@media(max-width:540px){
.work-toolbar-right{gap:6px}
.work-notifications>summary{padding:8px}
.work-toolbar>.work-tabs{flex-wrap:wrap}
}
"""
name = 'src/work-tasks.css'
text = (ROOT / name).read_text(encoding='utf-8')
if MARK not in text:
    prepared[name] = text + CSS

SCOPE = """
  function workAssigned(d,id) {
   let path=/databases/$(database)/documents/workTaskAccess/$(request.auth.uid+'_'+id);
   return exists(path) && get(path).data.active
    && (get(path).data.primaryThread=='main'
      ? request.auth.uid in d.get('directAssigneeIds',[])
      : exists(/databases/$(database)/documents/workTasks/$(id)/items/$(get(path).data.primaryThread))
       && !get(/databases/$(database)/documents/workTasks/$(id)/items/$(get(path).data.primaryThread)).data.deleted
       && request.auth.uid in get(/databases/$(database)/documents/workTasks/$(id)/items/$(get(path).data.primaryThread)).data.get('directAssigneeIds',[]));
  }
  function workScope(d,id) {
   return workUser() && (globalAccess() || d.branchIds.hasAny(profile().branchIds) || workAssigned(d,id));
  }
  function workWriteScope(id) {
   return workScope(workAfter(id),id) || (exists(/databases/$(database)/documents/workTasks/$(id)) && workScope(workRoot(id),id));
  }
""".strip('\n')

ACCESS = """
  match /workTaskAccess/{accessId} {
   function targetIds(d) {
    return d==null || d.deleted ? [] : d.get('directAssigneeIds',[]);
   }
   function nodeBefore(id,a) {
    return a.action in ['create','addItem'] ? null : a.thread=='main' ? workRoot(id) : get(/databases/$(database)/documents/workTasks/$(id)/items/$(a.thread)).data;
   }
   function nodeAfter(id,a) {
    return a.thread=='main' ? workAfter(id) : getAfter(/databases/$(database)/documents/workTasks/$(id)/items/$(a.thread)).data;
   }
   function validAccess() {
    let d=request.resource.data;
    let a=workLog(d.taskId);
    let old=resource==null ? [] : resource.data.sources;
    let was=d.uid in targetIds(nodeBefore(d.taskId,a));
    let now=d.uid in targetIds(nodeAfter(d.taskId,a));
    return d.keys().hasOnly(['uid','taskId','sources','primaryThread','active','updatedBy','updatedAt','lastActionId'])
     && d.uid is string && d.uid.size()>0 && d.uid.size()<=128 && d.uid.matches('[a-zA-Z0-9_-]+')
     && d.taskId is string && accessId==d.uid+'_'+d.taskId
     && d.sources is list && d.sources.size()<=101 && d.sources.toSet().size()==d.sources.size()
     && d.active==(d.sources.size()>0) && (d.active ? d.primaryThread in d.sources : d.primaryThread=='')
     && d.updatedBy==request.auth.uid && d.updatedAt==request.time && d.lastActionId==workAfter(d.taskId).lastActionId
     && a.action in ['create','edit','addItem','itemDelete','itemRestore'] && workPaired(d.taskId)
     && was==(a.thread in old) && was!=now
     && (now ? d.sources.toSet()==old.toSet().union([a.thread].toSet()) : d.sources.toSet()==old.toSet().difference([a.thread].toSet()));
   }
   allow get: if workUser() && (!exists(/databases/$(database)/documents/workTaskAccess/$(accessId)) || globalAccess() || resource.data.uid==request.auth.uid || workScope(workRoot(resource.data.taskId),resource.data.taskId));
   allow list: if workUser() && (globalAccess() || resource.data.uid==request.auth.uid);
   allow create,update: if workUser() && workWriteScope(request.resource.data.taskId) && validAccess();
   allow delete: if false;
  }
  match /workPeople/{uid} {
   allow read: if workUser() || (signedIn() && uid==request.auth.uid);
   allow create,update: if signedIn() && (globalAccess() || uid==request.auth.uid)
    && request.resource.data.keys().hasOnly(['username'])
    && request.resource.data.username is string && request.resource.data.username.size()>0 && request.resource.data.username.size()<=32
    && existsAfter(/databases/$(database)/documents/users/$(uid))
    && request.resource.data.username==getAfter(/databases/$(database)/documents/users/$(uid)).data.username;
   allow delete: if globalAccess() && !existsAfter(/databases/$(database)/documents/users/$(uid));
  }
""".strip('\n') + '\n'

change('firestore.rules', [
    (
        '  function workScope(d) { return workUser() && (globalAccess() || d.branchIds.hasAny(profile().branchIds)); }',
        SCOPE
    ),
    (
        '&& d.assignee is string && d.assignee.size()<=80',
        "&& d.assignee is string && d.assignee.size()<=80\n    && (!('directAssigneeIds' in d) || (d.directAssigneeIds is list && d.directAssigneeIds.size()<=100 && d.directAssigneeIds.toSet().size()==d.directAssigneeIds.size()))"
    ),
    (
        '  match /workReads/{receiptId} {',
        ACCESS + '  match /workReads/{receiptId} {'
    ),
])

REGISTER = """
    case "registerProfile": {
      if (auth.currentUser?.email !== loginEmail(data.username)) throw new Error("帳號不符");
      const ref = doc(db,"users",me), person = doc(db,"workPeople",me);
      await runTransaction(db,async transaction=>{
        const existing = await transaction.get(ref), directory = await transaction.get(person);
        const username = existing.exists()?existing.data().username:data.username;
        if(!existing.exists()) transaction.set(ref,{username,role:"pending",branchIds:[],mustChangePassword:false,createdAt:time()});
        if(!directory.exists()||directory.data().username!==username)transaction.set(person,{username});
      });
      return {};
    }
""".lstrip('\n')

name = 'src/api.ts'
text = (ROOT / name).read_text(encoding='utf-8')
if MARK not in text:
    pattern = r'    case "registerProfile": \{[\s\S]*?(?=    case "passwordChanged":)'
    text, count = re.subn(pattern, lambda _: REGISTER, text)
    if count != 1:
        raise RuntimeError('找不到註冊功能，未寫入任何檔案')
    start = text.index('    case "manageUser":')
    end = text.index('        } finally {', start)
    block = text[start:end]
    anchor = '          await batch.commit();'
    if block.count(anchor) != 1:
        raise RuntimeError('找不到建立帳號功能，未寫入任何檔案')
    block = block.replace(
        anchor,
        '          batch.set(doc(otherDb, "workPeople", user.user.uid), {username: data.username});\n' + anchor
    )
    text = text[:start] + block + text[end:]
    prepared[name] = text

change('src/delete-user.ts', [
    (
        'transaction.delete(targetRef);',
        'transaction.delete(targetRef);\n    transaction.delete(doc(db, "workPeople", data.uid));'
    )
])

change('src/main.tsx', [
    (
        'branchId={branchId} {...work}',
        'branchId={branchId} peopleUsers={users} onSelectBranch={setBranchId} {...work}'
    )
])

if 'firestore.rules' in prepared:
    text = prepared['firestore.rules']
    text = text.replace(
        "'assignee','due'",
        "'assignee','directAssigneeIds','due'"
    )
    text = text.replace(
        'workScope(resource.data)',
        'workScope(resource.data,id)'
    )
    text = text.replace(
        'workScope(workRoot(id))',
        'workScope(workRoot(id),id)'
    )
    text = text.replace(
        'workScope(workAfter(id))',
        'workWriteScope(id)'
    )
    text = text.replace(
        'workScope(workRoot(request.resource.data.taskId))',
        'workScope(workRoot(request.resource.data.taskId),request.resource.data.taskId)'
    )
    prepared['firestore.rules'] = text

PEOPLE = """import {useEffect,useRef,useState} from 'react';
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
"""

path = ROOT / 'src/work-people.ts'
if (
    path.exists()
    and MARK not in path.read_text(encoding='utf-8')
    and path.read_text(encoding='utf-8') != PEOPLE
):
    raise RuntimeError('work-people.ts 已存在不同版本，未寫入任何檔案')
prepared['src/work-people.ts'] = PEOPLE

for name, text in prepared.items():
    comment = (
        '\n/* ' + MARK + ' */\n'
        if name.endswith('.css')
        else '\n// ' + MARK + '\n'
    )
    (ROOT / name).write_text(text + comment, encoding='utf-8')
    print('已更新 ' + name)

print('完成。請發布 GitHub firestore.rules 到 Firebase，再以管理員登入待辦事項一次。')
