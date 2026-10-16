from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
changes = {}

component = """
import {useEffect,useRef,useState} from 'react';
import {doc,onSnapshot,runTransaction,serverTimestamp} from 'firebase/firestore';
import {Megaphone} from 'lucide-react';
import {auth,db} from './firebase';
import './branch-cheers.css';

type Row=Record<string,any>;

export function CheerText({text}:{text:string}){
 return text?<><Megaphone size={23} aria-hidden="true"/><span>{text}</span></>:null;
}

export function HeaderCheer({
 branchId,uid
}:{branchId:string|null;uid:string}){
 const [value,setValue]=useState({key:'',text:''});
 const key=uid+'/'+(branchId||'');

 useEffect(()=>{
  setValue({key,text:''});
  if(!branchId)return;
  return onSnapshot(
   doc(db,'branchCheers',branchId),
   s=>setValue({key,text:s.data()?.text||''}),
   ()=>setValue({key,text:''})
  );
 },[key]);

 const text=value.key===key?value.text:'';

 return <div
  className={'header-cheer'+(text?' has-text':'')}
  aria-label="據點信心喊話"
 ><CheerText text={text}/></div>;
}

export async function saveCheer(
 id:string,text:string,expected:number|null
){
 const uid=auth.currentUser?.uid;
 if(!uid)throw new Error('請先登入');

 const clean=text.trim();
 if(clean.length>200)throw new Error('信心喊話最多 200 字');

 const ref=doc(db,'branchCheers',id);

 return runTransaction(db,async tx=>{
  const old=await tx.get(ref);
  const revision=old.exists()?old.data().revision:null;

  if(revision!==expected)
   throw new Error('此據點的喊話已被其他人修改，請重新載入後再儲存');

  if(!clean){
   if(old.exists())tx.delete(ref);
   return null;
  }

  const next=(revision||0)+1;
  tx.set(ref,{
   text:clean,
   revision:next,
   updatedBy:uid,
   updatedAt:serverTimestamp()
  });
  return next;
 });
}

export default function BranchCheers({branches}:{branches:Row[]}){
 const available=branches.filter(b=>!b.archived);
 const [selected,setSelected]=useState('');
 const id=available.some(b=>b.id===selected)?
  selected:available[0]?.id||'';

 const [text,setText]=useState('');
 const [base,setBase]=useState<number|null>(null);
 const [ready,setReady]=useState(false);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 const [reload,setReload]=useState(0);

 const dirty=useRef(false);
 const generation=useRef(0);

 useEffect(()=>{
  const token=++generation.current;
  dirty.current=false;
  setText('');
  setBase(null);
  setReady(false);
  setError('');
  setNotice('');

  if(!id)return;

  return onSnapshot(doc(db,'branchCheers',id),s=>{
   if(token!==generation.current)return;
   if(!dirty.current){
    setText(s.data()?.text||'');
    setBase(s.exists()?s.data().revision:null);
   }
   setReady(true);
  },e=>{
   setError(e.message);
   setReady(false);
  });
 },[id,reload]);

 async function save(value=text){
  if(!id||!ready||busy)return;
  setBusy(true);
  setError('');
  setNotice('');
  const token=generation.current;

  try{
   const revision=await saveCheer(id,value,base);
   if(token!==generation.current)return;
   dirty.current=false;
   setText(value.trim());
   setBase(revision);
   setNotice(value.trim()?'信心喊話已儲存':'信心喊話已清除');
  }catch(e:any){
   if(token===generation.current)setError(e.message);
  }finally{
   setBusy(false);
  }
 }

 return <section className="panel cheer-editor">
  <p className="hint">
   選擇據點後設定文字，會顯示在該據點所有分頁最上方。
   未設定時不顯示文字或大聲公。
  </p>

  {!available.length?<p>目前沒有可設定的據點。</p>:<>
   <label>
    設定據點
    <select
     aria-label="信心喊話設定據點"
     value={id}
     disabled={busy}
     onChange={e=>{
      if(dirty.current&&!window.confirm(
       '尚有未儲存的文字，確定切換據點？'
      ))return;
      setSelected(e.target.value);
     }}
    >
     {available.map(b=>
      <option key={b.id} value={b.id}>{b.name}</option>
     )}
    </select>
   </label>

   <form onSubmit={e=>{
    e.preventDefault();
    void save();
   }}>
    <label>
     喊話內容
     <textarea
      aria-label="喊話內容"
      maxLength={200}
      rows={4}
      value={text}
      disabled={!ready||busy}
      placeholder="例如：每一次用心服務，都是讓客人安心的開始！"
      onChange={e=>{
       dirty.current=true;
       setText(e.target.value);
       setNotice('');
      }}
     />
    </label>

    <p className="hint">
     {text.length}／200 字；留空儲存即可移除顯示。
    </p>

    <div className="cheer-preview" aria-label="信心喊話預覽">
     <CheerText text={text.trim()}/>
    </div>

    {error&&
     <p role="alert" className="alert error">
      {error}
      <button type="button" disabled={busy} onClick={()=>{
       if(!dirty.current||window.confirm(
        '重新載入將捨棄尚未儲存的文字，確定繼續？'
       ))setReload(n=>n+1);
      }}>重新載入</button>
     </p>
    }

    {notice&&
     <p role="status" className="alert success">{notice}</p>
    }

    <div className="cheer-actions">
     <button type="submit" className="primary" disabled={!ready||busy}>
      {busy?'儲存中…':'儲存'}
     </button>
     <button
      type="button"
      className="secondary"
      disabled={!ready||busy||(!text&&base===null)}
      onClick={()=>{
       if(window.confirm('確定清除此據點的信心喊話？'))
        void save('');
      }}
     >清除喊話</button>
    </div>
   </form>
  </>}
 </section>;
}
"""

css = """
/* branch-cheers-v1 */
main > header {
 height:auto;
 min-height:75px;
 gap:20px;
 padding-top:14px;
 padding-bottom:14px;
}
main > header .breadcrumb,
main > header .header-right {
 flex-shrink:0;
}
.header-cheer {
 flex:1;
 min-width:0;
 display:flex;
 align-items:center;
 justify-content:center;
 gap:10px;
 color:#193e70;
 font-size:16px;
 font-weight:600;
}
.header-cheer svg,.cheer-preview svg {
 flex-shrink:0;
 color:#c58b00;
}
.header-cheer span,.cheer-preview span {
 white-space:pre-wrap;
 overflow-wrap:anywhere;
 min-width:0;
}
.cheer-editor { max-width:850px; }
.cheer-editor > label {
 max-width:400px;
 margin:20px 0;
}
.cheer-editor textarea { width:100%; }
.cheer-preview {
 min-height:70px;
 display:flex;
 gap:12px;
 align-items:center;
 border:1px solid #f0d47a;
 background:#fff3c4;
 border-radius:8px;
 padding:16px;
 margin:20px 0;
 color:#193e70;
}
.cheer-actions {
 display:flex;
 flex-wrap:wrap;
 gap:12px;
}
@media(max-width:1100px){
 main > header { flex-wrap:wrap; gap:10px; }
 main > header .header-right { margin-left:auto; }
 .header-cheer { display:none; }
 .header-cheer.has-text {
  display:flex;
  order:3;
  flex-basis:100%;
  justify-content:flex-start;
 }
}
@media(max-width:760px){
 main > header { min-height:60px; }
 .header-cheer { font-size:14px; }
}
.header-cheer.has-text {
 background:#fff3c4;
 border:1px solid #f0d47a;
 border-radius:8px;
 padding:10px 14px;
}
"""

p = root / 'src/main.tsx'
s = p.read_text(encoding='utf-8')

if 'import BranchCheers,' not in s:
    s = (
        'import BranchCheers,{HeaderCheer} from "./BranchCheers";\n'
        'import {Megaphone} from "lucide-react";\n'
    ) + s

    s = re.sub(
        r'(page\s*===\s*"users"\s*\|\|\s*page\s*===\s*"work")',
        'page === "cheers" || '+r'\1',
        s,
        count=1
    )

    old = '...(global ? [["users", "帳號與權限", Users]] : []),'
    if old not in s:
        raise SystemExit('找不到管理選單，未更動檔案。')

    s = s.replace(
        old,
        '...(global ? [["cheers", "信心喊話", Megaphone],'
        '["users", "帳號與權限", Users]] : []),',
        1
    )

    s = s.replace(
        '<div className="header-right">',
        '''<HeaderCheer
         uid={user.uid}
         branchId={
          profile&&(global||["manager","employee"].includes(profile.role))?
           (branchId!=="all"&&branches.some(b=>b.id===branchId&&!b.archived)?
            branchId:
            !global&&branches.filter(b=>!b.archived).length===1?
             branches.find(b=>!b.archived)!.id:null
           ):null
         }
        /><div className="header-right">''',
        1
    )

    s, count = re.subn(
        r'\{page\s*===\s*"manual"\s*\?\s*"依頁面查看功能說明與操作步驟。"',
        '{page === "cheers" ? "為各據點設定最上方的鼓勵文字。" '
        ': page === "manual" ? "依頁面查看功能說明與操作步驟。"',
        s,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到頁面標題，未更動檔案。')

    s = s.replace(
        'page !== "users" && page !== "manual" && (',
        'page !== "cheers" && page !== "users" && page !== "manual" && (',
        1
    )

    old = '{page === "manual" && <OperationManual/>}'
    if old not in s:
        raise SystemExit('找不到頁面區塊，未更動檔案。')

    s = s.replace(
        old,
        old+'\n'
        '{page === "cheers" && global && <BranchCheers branches={branches}/>}'
    )

changes['src/main.tsx'] = s
changes['src/BranchCheers.tsx'] = component
changes['src/branch-cheers.css'] = css

p = root / 'src/page-navigation.ts'
s = p.read_text(encoding='utf-8')

if "'cheers'" not in s:
    s = s.replace(
        "'users','manual'",
        "'users','manual','cheers'"
    )
    s = s.replace(
        "if(page==='users')",
        "if(['users','cheers'].includes(page))"
    )

changes['src/page-navigation.ts'] = s

p = root / 'firestore.rules'
s = p.read_text(encoding='utf-8')

if '// branch-cheers-v1' not in s:
    block = """
  // branch-cheers-v1
  match /branchCheers/{id} {
   allow read: if branchAccess(id);

   function validCheer(){
    let d=request.resource.data;
    return globalAccess()
     && exists(/databases/$(database)/documents/branches/$(id))
     && !get(/databases/$(database)/documents/branches/$(id)).data.get('archived',false)
     && d.keys().hasOnly(['text','revision','updatedBy','updatedAt'])
     && d.text is string
     && d.text.size()>0
     && d.text.size()<=200
     && d.revision is int
     && d.updatedBy==request.auth.uid
     && d.updatedAt==request.time;
   }

   allow create: if validCheer()
    && request.resource.data.revision==1;
   allow update: if validCheer()
    && request.resource.data.revision==resource.data.revision+1;
   allow delete: if globalAccess();
  }
"""
    index = s.index('match /users/{uid}')
    s = s[:index] + block + s[index:]

changes['firestore.rules'] = s

p = root / 'src/manual-content.ts'
s = p.read_text(encoding='utf-8')

if '// branch-cheers-manual-v1' not in s:
    s += """
// branch-cheers-manual-v1
manualPages.push({
 id:'cheers',
 title:'信心喊話',
 intro:'主管與管理員設定各據點所有頁面頂端的鼓勵文字。',
 access:'設定：主管／管理員；查看：具該據點權限的帳號',
 topics:[{
  title:'設定、預覽與清除喊話',
  steps:[
   '主管或管理員從左側點「信心喊話」，在設定據點選擇分店。',
   '輸入最多 200 字，預覽會顯示淡黃色底、深色文字與大聲公，按儲存後同步至該據點。',
   '選定該據點後，所有分頁最上方都會顯示；切換據點時改顯示對應文字。',
   '未設定、清除喊話或留空儲存後，不會顯示文字、底色及大聲公。「全部據點」不混合顯示；只有一間所屬據點的店長或員工自動顯示該店喊話。',
   '如其他主管同時修改，儲存會提示重新載入；先保留自己要用的文字，再重新載入確認。'
  ],
  result:'此設定不更動倉位、候補、待辦或 KPI。店長及員工沒有信心喊話設定選單，也不能修改設定。'
 }]
});
"""

changes['src/manual-content.ts'] = s

for name, content in changes.items():
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')

print('信心喊話與操作手冊更新完成。請完成建置並發布 Firestore 規則。')
