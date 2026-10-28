from pathlib import Path

root = Path(__file__).resolve().parents[1]
page = root / "src/WorkTasks.tsx"
manual = root / "src/manual-content.ts"
s = page.read_text(encoding="utf-8")

if "// my-work-scope-v1" not in s:
    anchor = (
        " const global=['admin','supervisor'].includes(profile.role),"
        "uid=auth.currentUser?.uid;"
    )
    if (
        "branchId,tasks,reads" not in s
        or '<div className="work-filters">' not in s
        or anchor not in s
    ):
        raise SystemExit("待辦頁面結構不同，尚未修改檔案。")

    s = s.replace(
        "branchId,tasks,reads",
        "branchId,tasks:allTasks,reads",
        1,
    )
    s = (
        "import {useMyWorkScope,WorkScopePicker} "
        "from './my-work-scope';\n"
    ) + s

    s = s.replace(
        anchor,
        anchor + """
 // my-work-scope-v1
 const {tasks,scope,setScope,scopeError}=useMyWorkScope(allTasks,profile);
 useEffect(()=>{
  if(focus?.id&&allTasks.some((t:WorkRow)=>t.id===focus.id)&&!tasks.some((t:WorkRow)=>t.id===focus.id))setScope('all');
 },[focus?.nonce,allTasks,tasks]);
""",
        1,
    )

    s = s.replace(
        '<div className="work-filters">',
        """<div className="work-filters">
<WorkScopePicker scope={scope} onChange={(value:string)=>{
 setScope(value);
 onSelectBranch?.('all');
 setSelected('');
 setThread('main');
}}/>
{scopeError&&<p role="alert" className="alert error">{scopeError}</p>}
""",
        1,
    )

    s = s.replace(
        "setNotice(`已發布 ${count} 份事項`);",
        "setNotice(`已發布 ${count} 份事項`);setScope('all');",
        1,
    )
    s = s.replace(
        "const edit=(kind:string)=>{setForm(",
        "const edit=(kind:string)=>{if(!item)return;setForm(",
        1,
    )

module = """import {useEffect,useState} from 'react';
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
"""

m = manual.read_text(encoding="utf-8")
m = m.replace(
    "進入待辦事項時，預設「全部可查看待辦（跨據點）」",
    "進入待辦事項時，預設範圍為「我的據點＋指派給我」，"
    "據點選單則為「全部可查看待辦（跨據點）」",
)

if "// my-work-scope-v1-manual" not in m:
    m += """
// my-work-scope-v1-manual
manualPages.find(p => p.id === 'work')?.topics.push({
 title:'我的據點與指派給我的待辦',
 steps:[
  '進入待辦預設「我的據點＋指派給我」：合併帳號所屬／負責據點的事項，以及其他據點直接指派給自己的主事項或子項目，同一事項只列一次。主管與管理員的據點依「我的負責據點」設定。',
  '需要完整管理清單時，將「待辦範圍」切成「全部可查看待辦」。切換範圍會清除單店篩選；也可再用上方據點選單縮小範圍。',
  '通知點入的事項若不在目前範圍，會切換全部可查看待辦並開啟該事項；自己發布新事項後也切換全部，方便核對。'
 ],
 result:'範圍只是清單篩選，不改變原本的存取權限及通知設定；未指派、也不屬於自己據點的事項不會列在預設清單。'
});
"""

page.write_text(s, encoding="utf-8")
(root / "src/my-work-scope.tsx").write_text(module, encoding="utf-8")
manual.write_text(m, encoding="utf-8")
print("已新增「我的據點＋指派給我」預設範圍及全部切換。")
