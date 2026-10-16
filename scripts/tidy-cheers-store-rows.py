from pathlib import Path

root = Path(__file__).resolve().parents[1]
changes = {}

component = """
import {useEffect,useRef,useState} from 'react';
import {collection,doc,onSnapshot,runTransaction,serverTimestamp} from 'firebase/firestore';
import {Megaphone} from 'lucide-react';
import {auth,db} from './firebase';
import './branch-cheers.css';

type Row=Record<string,any>;

export function CheerText({text}:{text:string}){
 return text?
  <span className="cheer-bubble" title={text}>
   <Megaphone size={23} aria-hidden="true"/>
   <span>{text}</span>
  </span>:null;
}

export function HeaderCheer({branchId,uid}:{branchId:string|null;uid:string}){
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

export async function saveCheer(id:string,text:string,expected:number|null){
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
 const [selected,setSelected]=useState<string[]|null>(null);
 const ids=(
  selected===null?(available[0]?[available[0].id]:[]):selected
 ).filter(id=>available.some(b=>b.id===id));
 const selectionKey=JSON.stringify(ids);

 const [text,setText]=useState('');
 const [base,setBase]=useState<Record<string,number|null>>({});
 const [records,setRecords]=useState<Record<string,Row>>({});
 const [ready,setReady]=useState(false);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [listError,setListError]=useState('');
 const [notice,setNotice]=useState('');
 const [reload,setReload]=useState(0);
 const dirty=useRef(false);

 useEffect(()=>onSnapshot(
  collection(db,'branchCheers'),
  s=>{
   setRecords(Object.fromEntries(
    s.docs.map(d=>[d.id,d.data()])
   ));
   setReady(true);
   setListError('');
  },
  e=>{
   setListError(e.message);
   setReady(false);
  }
 ),[reload]);

 useEffect(()=>{
  if(!ready||dirty.current)return;
  if(ids.length===1)setText(records[ids[0]]?.text||'');
  setBase(Object.fromEntries(
   ids.map(id=>[id,records[id]?.revision??null])
  ));
 },[ready,records,selectionKey,reload]);

 const configuredBranches=available.filter(
  b=>records[b.id]?.text?.trim()
 );

 function choose(next:string[]){
  if(busy)return;
  setBase(old=>Object.fromEntries(next.map(id=>[
   id,
   Object.hasOwn(old,id)?old[id]:records[id]?.revision??null
  ])));
  if(next.length>1)dirty.current=true;
  setSelected(next);
  setError('');
  setNotice('');
 }

 function edit(id:string){
  if(busy)return;
  if(dirty.current&&!window.confirm(
   '尚有未儲存的文字，確定切換據點？'
  ))return;

  dirty.current=false;
  setSelected([id]);
  setText(records[id]?.text||'');
  setBase({[id]:records[id]?.revision??null});
  setError('');
  setNotice('');
  setReload(n=>n+1);
  window.scrollTo({top:0,behavior:'smooth'});
 }

 async function save(value=text){
  if(!ids.length||!ready||busy)return;
  const clean=value.trim();
  setBusy(true);
  setError('');
  setNotice('');

  const done:Record<string,number|null>={};
  const failed:string[]=[];

  try{
   for(let offset=0;offset<ids.length;offset+=4){
    await Promise.all(ids.slice(offset,offset+4).map(async id=>{
     try{
      done[id]=await saveCheer(id,clean,base[id]??null);
     }catch(e:any){
      failed.push(
       (available.find(b=>b.id===id)?.name||id)+'：'+e.message
      );
     }
    }));
   }

   setBase(old=>({...old,...done}));
   setText(clean);
   const count=Object.keys(done).length;

   if(failed.length){
    dirty.current=true;
    setError(
     '已完成 '+count+' 間，其餘 '+failed.length+
     ' 間未更新。'+failed.join('；')
    );
   }else{
    dirty.current=false;
    setNotice(clean?
     '信心喊話已儲存，共 '+count+' 間':
     '信心喊話已清除，共 '+count+' 間'
    );
   }
  }finally{
   setBusy(false);
  }
 }

 return <section className="panel cheer-editor">
  <p className="hint">
   選擇一間或多間據點，將同一段文字套用到各店所有分頁最上方。
   未設定時不顯示文字或大聲公。
  </p>

  {!available.length?<p>目前沒有可設定的據點。</p>:<>
   <div className="cheer-target-select">
    <span id="cheer-target-label">設定據點</span>
    <details className="cheer-target-picker">
     <summary aria-labelledby="cheer-target-label">
      {ids.length===1?
       available.find(b=>b.id===ids[0])?.name:
       ids.length?'已選 '+ids.length+' 間據點':'請選擇據點'}
     </summary>

     <fieldset disabled={!ready||busy}>
      <legend className="sr-only">設定據點（可複選）</legend>
      <div className="cheer-target-tools">
       <button type="button" className="text-button"
        onClick={()=>choose(available.map(b=>b.id))}>全選</button>
       <button type="button" className="text-button"
        onClick={()=>choose([])}>取消全選</button>
       <span>已選 {ids.length} 間</span>
      </div>

      <div className="cheer-target-options">
       {available.map(b=>
        <label key={b.id}>
         <input
          type="checkbox"
          aria-label={'設定喊話據點 '+b.name}
          checked={ids.includes(b.id)}
          onChange={e=>choose(
           e.target.checked?
            [...ids,b.id]:ids.filter(id=>id!==b.id)
          )}
         />
         <span>{b.name}</span>
        </label>
       )}
      </div>
     </fieldset>
    </details>
   </div>

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
     {text.length}／200 字；已選 {ids.length} 間。
     儲存會覆蓋已選據點的喊話；留空儲存即可移除。
    </p>

    <div className="cheer-preview-block">
     <h3>頁面頂端預覽</h3>
     <div
      className={'cheer-preview'+(text.trim()?' has-text':'')}
      aria-label="信心喊話預覽"
     >
      {text.trim()?
       <CheerText text={text.trim()}/>:
       <span className="cheer-preview-empty">
        輸入文字後，這裡會顯示大聲公與喊話樣式。
       </span>
      }
     </div>
    </div>

    {(error||listError)&&
     <p role="alert" className="alert error">
      {error||listError}
      <button type="button" disabled={busy} onClick={()=>{
       if(dirty.current&&!window.confirm(
        '重新載入將捨棄尚未儲存的文字，確定繼續？'
       ))return;
       dirty.current=false;
       if(ids.length!==1)setText('');
       setError('');
       setReload(n=>n+1);
      }}>重新載入</button>
     </p>
    }

    {notice&&
     <p role="status" className="alert success">{notice}</p>
    }

    <div className="cheer-actions">
     <button type="submit" className="primary"
      disabled={!ready||busy||!ids.length}>
      {busy?'儲存中…':'儲存'}
     </button>
     <button type="button" className="secondary"
      disabled={!ready||busy||!ids.length}
      onClick={()=>{
       if(window.confirm(
        '確定清除已選 '+ids.length+' 間據點的信心喊話？'
       ))void save('');
      }}>清除喊話</button>
    </div>
   </form>

   <section className="cheer-configured" aria-label="已設定的據點">
    <h3>
     已設定的據點
     {ready&&<span> {configuredBranches.length} 間</span>}
    </h3>

    {listError?
     <p role="alert">無法載入已設定清單：{listError}</p>:
     !ready?<p>載入中…</p>:
     !configuredBranches.length?
      <p className="hint">目前沒有已設定喊話的據點。</p>:
      <div className="cheer-configured-grid">
       {configuredBranches.map(b=>
        <article key={b.id}>
         <div>
          <strong>{b.name}</strong>
          <button
           type="button"
           className="text-button"
           aria-label={'編輯 '+b.name+' 信心喊話'}
           disabled={busy}
           onClick={()=>edit(b.id)}
          >編輯</button>
         </div>
         <p>{records[b.id].text}</p>
        </article>
       )}
      </div>
    }
   </section>
  </>}
 </section>;
}
"""

changes['src/BranchCheers.tsx'] = component

p = root / 'src/branch-cheers.css'
s = p.read_text(encoding='utf-8')

if '/* cheer-refinement-v5 */' not in s:
    s += """
/* cheer-refinement-v5 */
.cheer-configured-grid {
 display:flex;
 flex-direction:column;
 gap:12px;
}
.cheer-configured-grid article {
 display:grid;
 grid-template-columns:120px minmax(0,1fr) auto;
 align-items:start;
 gap:16px;
 width:100%;
}
.cheer-configured-grid article > div { display:contents; }
.cheer-configured-grid article strong {
 grid-column:1;
 grid-row:1;
}
.cheer-configured-grid article p {
 grid-column:2;
 grid-row:1;
 margin:0;
}
.cheer-configured-grid article button {
 grid-column:3;
 grid-row:1;
 justify-self:end;
 white-space:nowrap;
}
@media(max-width:600px){
 .cheer-configured-grid article {
  grid-template-columns:minmax(0,1fr) auto;
  gap:10px;
 }
 .cheer-configured-grid article button { grid-column:2; }
 .cheer-configured-grid article p {
  grid-column:1/-1;
  grid-row:2;
 }
}

.header-cheer.has-text {
 background:transparent;
 border:0;
 padding:0;
}
.cheer-bubble {
 display:inline-flex;
 align-items:center;
 gap:10px;
 width:fit-content;
 max-width:100%;
 min-width:0;
 background:#fff3c4;
 border:1px solid #f0d47a;
 border-radius:8px;
 padding:8px 12px;
}
.cheer-bubble > span {
 display:block;
 min-width:0;
 white-space:nowrap;
 overflow:hidden;
 text-overflow:ellipsis;
}
.cheer-editor .cheer-preview.has-text {
 background:#f7f9fc;
 border-color:#dae3ed;
}

.cheer-target-select {
 display:flex;
 align-items:flex-start;
 gap:12px;
 margin:0 0 24px;
 max-width:600px;
}
.cheer-target-select > span {
 white-space:nowrap;
 padding-top:12px;
}
.cheer-target-picker {
 flex:1;
 min-width:0;
 border:1px solid #dae3ed;
 border-radius:8px;
 background:#fff;
}
.cheer-target-picker > summary {
 cursor:pointer;
 padding:12px;
}
.cheer-target-picker fieldset {
 margin:0;
 padding:12px;
 border:0;
}
.cheer-target-picker legend {
 font-size:12px;
 color:#718099;
}
.cheer-target-tools {
 display:flex;
 flex-wrap:wrap;
 align-items:center;
 gap:12px;
 margin-bottom:10px;
}
.cheer-target-tools > span {
 margin-left:auto;
 font-size:12px;
 color:#718099;
}
.cheer-target-options {
 display:grid;
 grid-template-columns:repeat(2,minmax(0,1fr));
 gap:8px;
 max-height:260px;
 overflow:auto;
}
.cheer-target-options label {
 display:flex!important;
 flex-direction:row!important;
 align-items:center;
 gap:8px;
 margin:0;
 min-width:0;
 padding:8px;
 border:1px solid #e3e9f1;
 border-radius:6px;
}
.cheer-target-options input {
 width:18px!important;
 height:18px;
 flex:0 0 18px;
}
.cheer-target-options span { overflow-wrap:anywhere; }
@media(max-width:600px){
 .cheer-target-options { grid-template-columns:1fr; }
}
"""

changes['src/branch-cheers.css'] = s

p = root / 'src/manual-content.ts'
s = p.read_text(encoding='utf-8')

if '每間據點以整列顯示' not in s:
    s = s.replace(
        '會列出已儲存的據點、文字及總間數；',
        '會列出已儲存的據點、文字及總間數；每間據點以整列顯示，'
        '依序排列據點名稱、喊話內容及編輯按鈕。'
    )

for old in [
    '也可在設定據點選擇分店。',
    '也可在「設定據點」旁的下拉選單選擇分店。',
    '也可在上方「設定據點」標籤下的下拉選單選擇分店。'
]:
    s = s.replace(
        old,
        '也可展開「設定據點」旁的下拉清單複選分店，支援全選與取消全選。'
        '多選時會將同一段文字覆蓋至全部已選據點；已設定清單的編輯只會選中該間。'
    )

s = s.replace(
    '淡黃色底、深色文字與大聲公',
    '僅包住文字與大聲公的淡黃色底，搭配深色文字'
)
if '超出可用寬度以「…」顯示' not in s:
    s = s.replace(
        '搭配深色文字',
        '搭配深色文字；喊話維持單行，超出可用寬度以「…」顯示，'
        '完整內容可在設定頁查看與編輯'
    )

if '批次儲存會列出成功間數及失敗據點' not in s:
    s = s.replace(
        '如其他主管同時修改，儲存會提示重新載入；',
        '批次儲存會列出成功間數及失敗據點，請核對已設定清單；'
        '如其他主管同時修改，儲存會提示重新載入；'
    )

changes['src/manual-content.ts'] = s

for name, content in changes.items():
    (root / name).write_text(content, encoding='utf-8')

print('完成：據點複選、逐列清單、內容黃底與省略號，操作手冊已同步更新。')
