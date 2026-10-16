from pathlib import Path
import re

r = Path(__file__).resolve().parents[1]
changes = {}

def load(p):
    return changes.get(
        str(p.relative_to(r)),
        p.read_text(encoding='utf-8')
    )

def save(p, s):
    changes[str(p.relative_to(r))] = s

if (
    (r/'src/WaitingBranches.tsx').exists()
    and 'rentWaitingUnit' in
    (r/'src/main.tsx').read_text(encoding='utf-8')
):
    print('這份更新已套用，不需重複執行。')
    raise SystemExit(0)

p = r/'src/waiting-list.ts'
s = load(p)
s += '''
export async function deleteWaitingNote(id:string,noteId?:string){
 if(!auth.currentUser)throw new Error('請先登入');
 const parent=doc(db,'waitingList',id);
 await runTransaction(db,async tx=>{
  const root=await tx.get(parent);
  if(!root.exists()||root.data().deleting)
   throw new Error('候補已刪除或正在刪除');
  if(noteId)tx.delete(doc(parent,'notes',noteId));
  else tx.update(parent,{
   note:'',
   revision:root.data().revision+1,
   updatedBy:auth.currentUser!.uid,
   updatedAt:serverTimestamp()
  });
 });
}
'''
save(p, s)

p = r/'src/WaitingNotes.tsx'
s = load(p).replace(
    '{addWaitingNote}',
    '{addWaitingNote,deleteWaitingNote}'
)
anchor = ' const entries='
s = s.replace(anchor, '''
 async function remove(noteId?:string){
  if(!rowId||busy||disabled||
   !window.confirm('確定刪除這筆備註？刪除後無法還原。'))return;
  setBusy(true);
  setError('');
  try{
   await deleteWaitingNote(rowId,noteId);
  }catch(e:any){
   setError(e.message);
  }finally{
   setBusy(false);
  }
 }
''' + anchor, 1)

s = s.replace(
    "{n.draftIndex>=0&&<>",
    """{n.draftIndex<0&&
     <button type="button"
      className="text-button danger waiting-note-delete"
      disabled={disabled||busy}
      aria-label={'刪除備註 '+n.text}
      onClick={()=>remove(n.id)}>刪除</button>
    }{n.draftIndex>=0&&<>"""
)
s = s.replace(
    '<small>原有備註（未記錄聯絡時間）</small>',
    '''<small>原有備註（未記錄聯絡時間）</small>
    {!onChange&&
     <button type="button"
      className="text-button danger waiting-note-delete"
      disabled={disabled||busy}
      aria-label="刪除原有備註"
      onClick={()=>remove()}>刪除</button>
    }'''
)
save(p, s)

p = r/'src/WaitingList.tsx'
s = load(p)
s = 'import WaitingBranches from "./WaitingBranches";\n' + s
s = s.replace(
    'state,focus,onFocus}',
    'state,focus,onFocus,onRent}'
).replace(
    'onFocus:(id:string|null)=>void}',
    'onFocus:(id:string|null)=>void;onRent:(unit:Row)=>Promise<void>}'
)
s = s.replace(
    '<section className="panel"><div className="table-wrap"><table>',
    '<section className="panel waiting-summary">'
    '<div className="table-wrap">'
    '<table className="waiting-list-table">',
    1
)

a = s.index('<section className="panel waiting-summary">')
b = s.index('</tbody>', a)
section = s[a:b]

section = section.replace(
    '<td>{branchText(r)}</td>',
    """<td><WaitingBranches labels={[
     ...r.branchIds.map((id:string)=>
      String(names.get(id)||'據點名稱載入中')),
     ...(r.otherBranches?['其它：'+r.otherBranches]:[])
    ]}/></td>"""
)

labels = iter([
    '登記日期', '姓名', '候補據點',
    '需求材積', '需求月租', '需求時間',
    '需求到期時間', '合適空倉', '狀態'
])
section = re.sub(
    r'<td>',
    lambda m: '<td data-label="'+next(labels)+'">',
    section
)
s = s[:a] + section + s[b:]

s = s.replace(
    'names={names}/>',
    """names={names}
     canRent={id=>
      ['admin','supervisor'].includes(profile.role)||
      (profile.role==='manager'&&
       (profile.branchIds||[]).includes(id))}
     onRent={async unit=>{
      if(hasUnaddedNote&&!window.confirm(
       '尚有未儲存的備註，離開後不會保留，確定前往承租？'
      ))return;
      await onRent({...unit,waitingId:row.id});
      setSelected(null);
     }}/>""",
    1
)
s = s.replace(
    '<WaitingNotes rowId={row.id} legacy={row.note} disabled={!!row.deleting}/>',
    '<WaitingNotes rowId={row.id} legacy={row.note} '
    'disabled={!!row.deleting} onPendingChange={setHasUnaddedNote}/>'
)
save(p, s)

p = r/'src/WaitingMatches.tsx'
s = load(p)

s = re.sub(
    r'(branchIds,\s*names)(\s*\})',
    r'\1,canRent,onRent\2',
    s,
    count=1
)
s = re.sub(
    r'(names:\s*Map<string,\s*any>);?',
    r'\1;canRent:(id:string)=>boolean;onRent:(unit:Row)=>Promise<void>;',
    s,
    count=1
)

s = s.replace(
    " const [chosen,setChosen]",
    """ const [opening,setOpening]=useState(false);
 const [rentError,setRentError]=useState('');
 async function rent(unit:Row){
  if(opening)return;
  setOpening(true);
  setRentError('');
  try{
   await onRent(unit);
  }catch(e:any){
   setRentError(e.message);
  }finally{
   setOpening(false);
  }
 }
 const [chosen,setChosen]"""
)
s = s.replace(
    '<td>{u.code}</td>',
    """<td>{canRent(u.branchId)?
     <button type="button" className="text-button"
      aria-label={'承租 '+u.code}
      disabled={opening}
      onClick={()=>rent(u)}>{u.code}</button>:
     <span title="僅限該據點店長、主管或管理員辦理承租">
      {u.code}
     </span>
    }</td>"""
)
s = s.replace(
    '  {invalid&&',
    '  {rentError&&<p role="alert" className="alert error">'
    '{rentError}</p>}\n  {invalid&&',
    1
)
save(p, s)

p = r/'src/main.tsx'
s = load(p)
s = s.replace(
    'onFocus={setWaitingFocus}/>',
    'onFocus={setWaitingFocus} onRent={rentWaitingUnit}/>',
    1
)
anchor = '  const stats = (targetMonth: string) => {'
s = s.replace(anchor, '''
  async function rentWaitingUnit(unit:Row){
    const id=unit.branchId;
    if(!profile||
     (!["admin","supervisor"].includes(profile.role)&&
      !(profile.role==="manager"&&
       (profile.branchIds||[]).includes(id))))
     throw new Error("沒有此據點的承租操作權限");

    const [branchSnapshot,unitSnapshot]=await Promise.all([
     getDoc(doc(db,"branches",id)),
     getDoc(doc(db,"branches",id,"units",unit.code))
    ]);

    if(!branchSnapshot.exists()||
     branchSnapshot.data().archived||
     branchSnapshot.data().importing)
     throw new Error("據點正在匯入或已停用，請稍後再試");

    if(!unitSnapshot.exists()||
     unitSnapshot.data().status!=="vacant"||
     unitSnapshot.data().missing||
     unitSnapshot.data().archived)
     throw new Error("此倉位已非可承租空倉，請重新確認配對");

    setError("");
    setNotice("");
    setBranchId(id);
    setMonth(today().slice(0,7));
    setSearch(unit.code);
    setStatus("vacant");
    setPage("units");

    setModal({
     kind:"event",
     type:"new",
     unit:{
      ...unitSnapshot.data(),
      branchId:id,
      branchName:branchSnapshot.data().name
     },
     eventMonth:today().slice(0,7),
     waitingId:unit.waitingId
    });
  }
''' + anchor, 1)

s = s.replace(
    'type: modal.type,',
    'type: modal.type, waitingId: modal.waitingId,',
    1
)
save(p, s)

p = r/'firestore.rules'
s = load(p)
old = (
    "allow delete: if waitingScope(get(/databases/$(database)/documents/"
    "waitingList/$(id)).data) && get(/databases/$(database)/documents/"
    "waitingList/$(id)).data.get('deleting',false);"
)
if old not in s:
    raise SystemExit('找不到備註刪除規則，未更動檔案。')

s = s.replace(
    old,
    "allow delete: if waitingScope(get(/databases/$(database)/documents/"
    "waitingList/$(id)).data);"
)
save(p, s)

p = r/'src/api.ts'
s = load(p)
a = s.index('    case "recordEvent":')
b = s.index('    case "', a+10)
part = s[a:b]

if 'waitingRef=data.waitingId?' not in part:
    pattern = r'await runTransaction\(db,\s*async\s*\((\w+)\)\s*=>\s*\{'
    match = re.search(pattern, part)
    if not match:
        raise SystemExit('找不到承租交易，未更動檔案。')

    tx = match.group(1)

    declaration = '''
      if(data.waitingId&&
       (type!=="new"||
        typeof data.waitingId!=="string"||
        data.waitingId.includes("/")))
       throw new Error("候補承租資料不正確");
      const waitingRef=data.waitingId?
       doc(db,"waitingList",data.waitingId):null;
'''
    part = part[:match.start()] + declaration + part[match.start():]
    match = re.search(pattern, part)

    validation = (
        f'\n        const waitingSnapshot=waitingRef?'
        f'await {tx}.get(waitingRef):null;\n'
    ) + '''
        if(waitingRef&&(
         !waitingSnapshot?.exists()||
         waitingSnapshot.data().deleting||
         !['waiting','contacted','visit'].includes(
          waitingSnapshot.data().status
         )||
         !waitingSnapshot.data().branchIds.includes(branchId)
        ))throw new Error(
         "候補已刪除、狀態已變更或未包含此據點，請重新確認"
        );
'''
    part = part[:match.end()] + validation + part[match.end():]

    update = (
        f'        if(waitingRef&&waitingSnapshot){tx}.update(waitingRef,'
        '{status:"rented",revision:waitingSnapshot.data()!.revision+1,'
        'updatedBy:me,updatedAt:time()});\n'
    )
    part, count = re.subn(
        r'(?=        const delta\s*=)',
        lambda m: update,
        part,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到承租統計，未更動檔案。')
    s = s[:a] + part + s[b:]

save(p, s)

p = r/'src/WaitingBranches.tsx'
save(p, '''
import {useState} from 'react';

export default function WaitingBranches({labels}:{labels:string[]}){
 const [expanded,setExpanded]=useState(false);
 return <span className="waiting-branch-summary">
  {(expanded?labels:labels.slice(0,4)).join('、')}
  {labels.length>4&&
   <button type="button" className="text-button"
    aria-label={expanded?'收合候補據點':'展開全部候補據點'}
    onClick={()=>setExpanded(v=>!v)}>
    {expanded?'收合':'…'}
   </button>
  }
 </span>;
}
''')

p = r/'src/waiting-list.css'
s = load(p)
s += '''
/* waiting-summary-actions-v1 */
.waiting-summary { min-width:0; }
.waiting-summary .table-wrap { overflow:visible; }
.waiting-summary table {
 table-layout:fixed;
 width:100%;
 white-space:normal;
}
.waiting-summary th,.waiting-summary td {
 padding:12px 8px;
 overflow-wrap:anywhere;
 vertical-align:top;
}
.waiting-summary th:nth-child(1) { width:9%; }
.waiting-summary th:nth-child(2) { width:8%; }
.waiting-summary th:nth-child(3) { width:25%; }
.waiting-summary th:nth-child(4),
.waiting-summary th:nth-child(5) { width:10%; }
.waiting-summary th:nth-child(6),
.waiting-summary th:nth-child(7) { width:11%; }
.waiting-summary th:nth-child(8),
.waiting-summary th:nth-child(9) { width:8%; }
.waiting-branch-summary {
 white-space:normal;
 overflow-wrap:anywhere;
 line-height:1.7;
}
.waiting-branch-summary button { margin-left:4px; }
.waiting-note-delete { margin-left:auto; }

@media(max-width:900px){
 .waiting-summary thead { display:none; }
 .waiting-summary table,.waiting-summary tbody {
  display:block;
  width:100%;
 }
 .waiting-summary tr {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:12px 16px;
  padding:16px;
  border-bottom:1px solid #dae3ed;
 }
 .waiting-summary td {
  display:block;
  border:0;
  padding:0;
  min-width:0;
 }
 .waiting-summary td::before {
  content:attr(data-label);
  display:block;
  color:#718099;
  font-size:12px;
  margin-bottom:5px;
 }
 .waiting-summary td:nth-child(3) { grid-column:1/-1; }
}
'''
save(p, s)

p = r/'src/manual-waiting.ts'
s = load(p)
s = s.replace(
    '已保存的聯絡紀錄逐筆保留；不會覆蓋舊內容。',
    '已保存的聯絡紀錄逐筆保留；有候補權限的人可按該筆「刪除」並確認，'
    '刪除後無法還原。原有單一備註可在明細直接刪除。'
)
s = s.replace(
    '勾選已承租不會自動建立租約，仍需到倉位管理登記。',
    '手動勾選已承租不會建立租約；從合適空倉點倉號並完成承租'
    '則會同時自動切為已承租。'
)

topic = '''
 {
  title:'多據點收合、刪除備註與直接承租',
  steps:[
   '列表先顯示前四間候補據點，超過以「…」收合；點擊可展開，再按收合恢復。手機改為分項顯示，不需往右滑。',
   '備註旁點刪除並確認，即時刪除該筆；尚未儲存的備註使用移除。原有單一備註可在明細刪除。',
   '在合適空倉點倉號，系統重新確認仍為空倉，切至該據點倉位管理並開啟承租表單，填異動日期、租期及適用活動後確認儲存。',
   '只有該據點店長、主管與管理員可以點選承租；其他店空倉仍可查看配對。開啟表單不會預留或自動承租，存檔會再檢查倉位狀態。'
  ],
  result:'承租完成後依原規則記錄新承租；從候補開啟的承租儲存成功後，該筆候補會同時自動切為已承租並停止配對；如仍需候補，可手動改回待聯絡、已聯絡或待參觀。取消表單不會變更倉位或候補。'
 },
'''
s, count = re.subn(
    r'(export const waitingManual[\s\S]*?topics\s*:\s*\[)',
    lambda m: m.group(1) + topic,
    s,
    count=1
)
if count != 1:
    raise SystemExit('找不到候補操作手冊，未更動檔案。')

save(p, s)

for name, content in changes.items():
    p = r/name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')

print('完成：據點收合、備註刪除、直接承租並自動切已承租。請發布 Firestore 規則。')
