
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
