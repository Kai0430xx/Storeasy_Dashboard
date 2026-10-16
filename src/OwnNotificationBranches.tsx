
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
