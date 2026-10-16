
import {useEffect,useRef,useState} from 'react';
import {collection,doc,onSnapshot,runTransaction,serverTimestamp} from 'firebase/firestore';
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

 
 const [configured,setConfigured]=useState<Record<string,string>>({});
 const [configuredReady,setConfiguredReady]=useState(false);
 const [configuredError,setConfiguredError]=useState('');

 useEffect(()=>onSnapshot(
  collection(db,'branchCheers'),
  snapshot=>{
   setConfigured(Object.fromEntries(
    snapshot.docs.map(d=>[d.id,d.data().text||''])
   ));
   setConfiguredReady(true);
   setConfiguredError('');
  },
  e=>{
   setConfiguredError(e.message);
   setConfiguredReady(false);
  }
 ),[]);

 const configuredBranches=available.filter(
  b=>configured[b.id]?.trim()
 );
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

   <section className="cheer-configured" aria-label="已設定的據點">
    <h3>
     已設定的據點
     {configuredReady&&<span> {configuredBranches.length} 間</span>}
    </h3>

    {configuredError?
     <p role="alert" className="alert error">
      無法載入已設定清單：{configuredError}
     </p>:
     !configuredReady?<p>載入中…</p>:
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
           onClick={()=>{
            if(b.id!==id&&dirty.current&&!window.confirm(
             '尚有未儲存的文字，確定切換據點？'
            ))return;
            setSelected(b.id);
            window.scrollTo({top:0,behavior:'smooth'});
           }}
          >編輯</button>
         </div>
         <p>{configured[b.id]}</p>
        </article>
       )}
      </div>
    }
   </section>
  </>}
 </section>;
}
