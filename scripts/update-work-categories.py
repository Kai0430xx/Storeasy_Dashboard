from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARK = 'storeasy-work-categories-v1'
prepared = {}


def once(s, old, new, count=1):
    if s.count(old) != 1:
        raise RuntimeError('版本不符，未寫入任何檔案：' + old[:90])
    return s.replace(old, new, 1)


p = ROOT / 'src/WorkTasks.tsx'
s = p.read_text(encoding='utf-8')
if MARK not in s:
    s = 'import {useWorkCategories,addWorkCategory,permanentlyDeleteWorkTask} from "./work-categories";\n' + s

    s = once(
        s,
        "const empty={title:''",
        "const empty={category:'其它',title:''"
    )
    s = once(
        s,
        'function Fields({value,onChange,people}:any){return <>',
        'function Fields({value,onChange,people,categories,showCategory}:any){return <>{showCategory&&<label>分類<select aria-label="事項分類" value={value.category||\'其它\'} onChange={e=>onChange({...value,category:e.target.value})}>{categories.map((name:string)=><option key={name} value={name}>{name}</option>)}</select></label>}'
    )
    s = once(
        s,
        ' const people=useWorkPeople(profile,peopleUsers);',
        ' const people=useWorkPeople(profile,peopleUsers);\n const categories=useWorkCategories();\n const [category,setCategory]=useState(\'all\');'
    )
    s = once(
        s,
        ' const visible=tasks.filter',
        ' const filtered=tasks.filter'
    )
    pos = s.index(' const item=thread===')
    s = (
        s[:pos]
        + " const visible=filtered.filter((t:WorkRow)=>category==='all'||(t.category||'其它')===category);\n"
        + s[pos:]
    )
    s = once(
        s,
        ' const inactive=!task||task.deleted||item?.deleted;',
        ' const inactive=!task||task.deleted||task.purging||item?.deleted;'
    )
    s = once(
        s,
        '}:{...empty});setDialog({kind});',
        '}:{...empty,category:task?.category||\'其它\'});setDialog({kind});'
    )
    s = once(
        s,
        '{people.error&&',
        '{categories.error&&<div className="alert error" role="alert">{categories.error}</div>}{people.error&&'
    )
    s = once(
        s,
        "setForm({...empty,mode:'single'",
        "setForm({...empty,category:category==='all'?'其它':category,mode:'single'"
    )

    anchor = '  <div className="work-filters">'
    s = once(
        s,
        anchor,
        '''  <div className="work-categories" aria-label="事項分類"><button type="button" aria-pressed={category==='all'} className={category==='all'?'selected':''} onClick={()=>setCategory('all')}>全部 <span>{filtered.length}</span></button>{categories.options.map(name=><button type="button" key={name} aria-pressed={category===name} className={category===name?'selected':''} onClick={()=>setCategory(name)}>{name} <span>{filtered.filter((t:WorkRow)=>(t.category||'其它')===name).length}</span></button>)}{global&&<button type="button" className="text-button" onClick={()=>{setForm({name:''});setDialog({kind:'category'});}}>＋ 新增分類</button>}</div>
'''
        + anchor
    )
    s = once(
        s,
        '<span>建立者：{item.createdName}</span>',
        '<span>分類：{task.category||\'其它\'}</span><span>建立者：{item.createdName}</span>'
    )
    s = once(
        s,
        "{inactive&&global&&<button disabled={busy} onClick={()=>action(thread==='main'?'restore':'itemRestore')}>還原</button>}",
        "{inactive&&global&&!task.purging&&<button disabled={busy} onClick={()=>action(thread==='main'?'restore':'itemRestore')}>還原</button>}{task.deleted&&global&&thread==='main'&&<button className=\"text-button danger\" disabled={busy} onClick={()=>{if(window.confirm('永久刪除此事項？所有子項目、訊息、操作紀錄與已讀紀錄都會清除，無法還原。'))perform(async()=>{await permanentlyDeleteWorkTask(profile,task.id);setSelected('');setThread('main');},'已永久刪除');}}>{task.purging?'繼續永久刪除':'永久刪除'}</button>}"
    )
    s = once(
        s,
        "{dialog.kind==='create'?'新增事項':",
        "{dialog.kind==='category'?'新增分類':dialog.kind==='create'?'新增事項':"
    )
    s = once(
        s,
        "{dialog.kind==='history'?",
        "{dialog.kind==='category'?<form onSubmit={e=>{e.preventDefault();perform(async()=>{await addWorkCategory(profile,form.name);setDialog(null);});}}><label>分類名稱<input autoFocus required maxLength={30} value={form.name} onChange={e=>setForm({name:e.target.value})}/></label>{error&&<div className=\"alert error\">{error}</div>}<button disabled={busy}>{busy?'儲存中…':'新增'}</button></form>:dialog.kind==='history'?"
    )
    s = once(
        s,
        '<Fields value={form} onChange={setForm} people={people.options}/>',
        "<Fields value={form} onChange={setForm} people={people.options} categories={categories.options} showCategory={dialog.kind==='create'||dialog.kind==='edit'&&thread==='main'}/>"
    )
    s = once(
        s,
        "onSelectBranch?.('all');setMode",
        "onSelectBranch?.('all');setCategory('all');setMode"
    )
    s = once(
        s,
        "useEffect(()=>{if(task&&(branchId!=='all'&&!task.branchIds.includes(branchId))){setSelected('');setThread('main');}},[branchId,task?.id]);",
        "useEffect(()=>{if(task&&(branchId!=='all'&&!task.branchIds.includes(branchId)||category!=='all'&&(task.category||'其它')!==category)){setSelected('');setThread('main');}},[branchId,category,task?.id,task?.category]);"
    )
    prepared['src/WorkTasks.tsx'] = s


p = ROOT / 'src/work-tasks.ts'
s = p.read_text(encoding='utf-8')
if MARK not in s:
    s = once(
        s,
        "const result={title:",
        "const result={category:String(input.category||'其它'),title:"
    )
    s = once(
        s,
        "if(!result.title",
        "if(!result.category||result.category.length>30||result.category.includes('/'))throw new Error('分類不合法');\n if(!result.title"
    )
    s = once(
        s,
        "if(r.deleted&&action",
        "if(r.purging)throw new Error('事項正在永久刪除，請完成清除後再操作');\n  if(r.deleted&&action"
    )
    prepared['src/work-tasks.ts'] = s


p = ROOT / 'firestore.rules'
s = p.read_text(encoding='utf-8')
if MARK not in s:
    pos = s.index('  function workUser()')
    s = s[:pos] + '''  function workPurging(id) {
   return globalAccess() && exists(/databases/$(database)/documents/workTasks/$(id))
    && workRoot(id).deleted && workRoot(id).get('purging',false)==true;
  }
  match /workCategories/{name} {
   allow read: if workUser();
   allow create: if globalAccess() && name.size()>0 && name.size()<=30 && !(name in ['.','..'])
    && request.resource.data.keys().hasOnly(['name','createdBy','createdAt'])
    && request.resource.data.name==name && request.resource.data.createdBy==request.auth.uid && request.resource.data.createdAt==request.time;
   allow update,delete: if false;
  }
''' + s[pos:]

    s = s.replace(
        'return d.title is string',
        "return (!('category' in d) || (d.category is string && (d.category in ['店務','工務','IT','行銷','其它'] || exists(/databases/$(database)/documents/workCategories/$(d.category)))))\n    && d.title is string",
        1
    )

    start = s.index('  function workFields')
    end = s.index('  match /workTaskAccess')
    block = s[start:end].replace(
        "'title','description','assignee'",
        "'category','title','description','assignee'"
    )
    block = block.replace(
        "'lastActionId','signals'])",
        "'lastActionId','signals','purging'])",
        1
    )
    block = block.replace(
        'allow create: if workUser() && validRoot(request.resource.data)',
        "allow create: if workUser() && request.resource.data.get('purging',false)==false && validRoot(request.resource.data)",
        1
    )
    block = block.replace(
        'allow update: if workScope(resource.data,id)',
        "allow update: if resource.data.get('purging',false)==false && workScope(resource.data,id)",
        1
    )
    block = block.replace(
        '   allow delete: if false;',
        '''   allow update: if globalAccess() && resource.data.deleted && request.resource.data.purging==true
    && request.resource.data.diff(resource.data).affectedKeys().hasOnly(['purging']);
   allow delete: if workPurging(id);''',
        1
    )
    block = block.replace(
        '    allow update,delete: if false;',
        '    allow update: if false;\n    allow delete: if workPurging(id);'
    )
    block = block.replace(
        '    allow delete: if false;',
        '    allow delete: if workPurging(id);'
    )
    block = block.replace(
        '!workRoot(id).deleted',
        "!workRoot(id).deleted && workRoot(id).get('purging',false)==false"
    )
    block += '''  match /workTasks/{id}/threads/{thread} {
   allow read,delete: if workPurging(id);
   allow create,update: if false;
  }
'''
    s = s[:start] + block + s[end:]

    start = s.index('  match /workTaskAccess')
    end = s.index('  match /workPeople')
    block = s[start:end].replace(
        'allow delete: if false;',
        'allow delete: if workPurging(resource.data.taskId);'
    )
    s = s[:start] + block + s[end:]

    start = s.index('  match /workReads')
    end = s.index('  match /{document=**}', start)
    block = s[start:end].replace(
        'allow list: if workUser() && resource.data.uid==request.auth.uid;',
        'allow list: if workUser() && (resource.data.uid==request.auth.uid || workPurging(resource.data.taskId));'
    )
    block = block.replace(
        'allow delete: if false;',
        'allow delete: if workPurging(resource.data.taskId);'
    )
    s = s[:start] + block + s[end:]
    prepared['firestore.rules'] = s


p = ROOT / 'src/work-tasks.css'
s = p.read_text(encoding='utf-8')
if MARK not in s:
    prepared['src/work-tasks.css'] = s + '''
/* storeasy-work-categories-v1 */
.work-categories{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:12px 0 16px}
.work-categories>button{border:1px solid #dce5f1;border-radius:8px;padding:8px 12px;font-size:13px;background:#fff;color:#173f75}
.work-categories>button.selected{background:#173f75;color:#fff;border-color:#173f75}
.work-categories>button>span{margin-left:5px;font-variant-numeric:tabular-nums;opacity:.8}
'''


MODULE = r"""import {useEffect,useState} from 'react';
import {collection,doc,onSnapshot,setDoc,serverTimestamp,query,where,getDocs,getDoc,limit,writeBatch,runTransaction} from 'firebase/firestore';
import {auth,db} from './firebase';
import {WorkRow,workError} from './work-tasks';

export const defaultWorkCategories=['店務','工務','IT','行銷','其它'];

export function useWorkCategories(){
 const [custom,setCustom]=useState<string[]>([]),[error,setError]=useState('');
 useEffect(()=>onSnapshot(
  collection(db,'workCategories'),
  s=>setCustom(s.docs.map(d=>d.id).sort((a,b)=>a.localeCompare(b,'zh-Hant'))),
  e=>setError(workError(e))
 ),[]);
 return {
  options:[...defaultWorkCategories,...custom.filter(n=>!defaultWorkCategories.includes(n))],
  error
 };
}

export async function addWorkCategory(profile:WorkRow,name:string){
 name=name.trim();
 if(!['admin','supervisor'].includes(profile.role))throw new Error('僅主管與管理員可新增分類');
 if(!name||name.length>30||name.includes('/')||name==='.'||name==='..')throw new Error('分類須為1～30字，不能包含斜線');
 if(defaultWorkCategories.includes(name)||(await getDoc(doc(db,'workCategories',name))).exists())throw new Error('此分類已存在');
 await setDoc(doc(db,'workCategories',name),{
  name,
  createdBy:auth.currentUser!.uid,
  createdAt:serverTimestamp()
 });
}

export async function permanentlyDeleteWorkTask(profile:WorkRow,taskId:string){
 if(!['admin','supervisor'].includes(profile.role))throw new Error('僅主管與管理員可永久刪除');
 const root=doc(db,'workTasks',taskId);
 const data=await runTransaction(db,async tx=>{
  const s=await tx.get(root);
  if(!s.exists())throw new Error('事項不存在');
  const d=s.data();
  if(!d.deleted)throw new Error('請先將事項移到垃圾桶');
  if(!d.purging)tx.update(root,{purging:true});
  return d;
 });
 const children=await getDocs(collection(root,'items'));
 const threads=new Set([
  'main',
  ...Object.keys(data.signals||{}),
  ...children.docs.map(d=>d.id)
 ]);
 const clear=async(q:any)=>{
  for(;;){
   const s=await getDocs(query(q,limit(200)));
   if(s.empty)return;
   const batch=writeBatch(db);
   s.docs.forEach((d:any)=>batch.delete(d.ref));
   await batch.commit();
  }
 };
 // 根文件最後刪除，途中中斷可繼續清除。
 for(const thread of threads)await clear(collection(root,'threads',thread,'messages'));
 await clear(collection(root,'threads'));
 await clear(collection(root,'items'));
 await clear(collection(root,'history'));
 await clear(collection(root,'versions'));
 await clear(query(collection(db,'workTaskAccess'),where('taskId','==',taskId)));
 await clear(query(collection(db,'workReads'),where('taskId','==',taskId)));
 const batch=writeBatch(db);
 batch.delete(root);
 await batch.commit();
}
"""

p = ROOT / 'src/work-categories.ts'
if p.exists() and MARK not in p.read_text(encoding='utf-8'):
    raise RuntimeError('work-categories.ts 已存在不同版本，未寫入任何檔案')
if not p.exists():
    prepared['src/work-categories.ts'] = MODULE

for name, text in prepared.items():
    suffix = (
        '\n/* ' + MARK + ' */\n'
        if name.endswith('.css')
        else '\n// ' + MARK + '\n'
    )
    (ROOT / name).write_text(text + suffix, encoding='utf-8')
    print('已更新 ' + name)

print('完成。請將 GitHub 最新 firestore.rules 全文發布到 Firebase。')
