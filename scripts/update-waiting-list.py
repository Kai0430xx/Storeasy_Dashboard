from pathlib import Path
import re

WAITING_RULES = r'''
  // storeasy-waiting-list-v1
  function waitingScope(d) {
   return workUser() && (globalAccess() || d.createdBy==request.auth.uid || d.branchIds.hasAny(profile().branchIds));
  }
  function waitingNumber(d,k) { return d[k]==null || (d[k] is number && d[k]>=0 && d[k]<=100000000); }
  function waitingRange(d,lo,hi) { return waitingNumber(d,lo) && waitingNumber(d,hi) && (d[lo]==null || d[hi]==null || d[lo]<=d[hi]); }
  function validWaiting(d) {
   return d.keys().hasOnly(['date','name','phone','email','needed','items','note','branchIds','otherBranches','volumeMin','volumeMax','priceMin','priceMax','status','createdBy','createdAt','updatedBy','updatedAt','revision'])
    && d.date is string && d.date.matches('20[0-9]{2}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])')
    && d.name is string && d.name.size()>0 && d.name.size()<=80
    && d.phone is string && d.phone.matches('[0-9]{0,4}')
    && d.email is string && d.email.size()<=254 && (d.email=='' || d.email.matches('[^ @]+@[^ @]+[.][^ @]+'))
    && d.needed is string && (d.needed=='' || d.needed.matches('(0[1-9]|1[0-2])/(0[1-9]|[12][0-9]|3[01])'))
    && d.items is string && d.items.size()>0 && d.items.size()<=500
    && d.note is string && d.note.size()<=1000
    && d.branchIds is list && d.branchIds.size()<=100 && d.branchIds.toSet().size()==d.branchIds.size()
    && d.otherBranches is string && d.otherBranches.size()<=300 && (d.branchIds.size()>0 || d.otherBranches.size()>0)
    && waitingRange(d,'volumeMin','volumeMax') && waitingRange(d,'priceMin','priceMax')
    && d.status in ['waiting','rented','cancelled'] && d.updatedBy==request.auth.uid && d.updatedAt==request.time;
  }
  match /waitingList/{id} {
   allow get: if workUser() && (!exists(/databases/$(database)/documents/waitingList/$(id)) || waitingScope(resource.data));
   allow list: if waitingScope(resource.data);
   allow create: if workUser() && validWaiting(request.resource.data) && request.resource.data.createdBy==request.auth.uid && request.resource.data.createdAt==request.time && request.resource.data.revision==1;
   allow update: if waitingScope(resource.data) && validWaiting(request.resource.data)
    && request.resource.data.createdBy==resource.data.createdBy && request.resource.data.createdAt==resource.data.createdAt
    && request.resource.data.revision==resource.data.revision+1;
   allow delete: if waitingScope(resource.data);
  }
  match /waitingReads/{uid}/items/{id} {
   allow read,delete: if workUser() && uid==request.auth.uid;
   allow create,update: if workUser() && uid==request.auth.uid
    && request.resource.data.keys().hasOnly(['seen']) && request.resource.data.seen is list && request.resource.data.seen.size()<=2000;
  }
  function waitingStockData(id,code,u) {
   return {'branchId':id,'code':code,'volume':u.volume,'price':u.price,'vacantSince':u.get('vacantSince',null),'lastEventId':u.get('lastEventId',null),'lastEventDate':u.get('lastEventDate',null)};
  }
  function waitingVacant(u) { return u.get('status','')=='vacant' && !u.get('missing',false) && !u.get('archived',false); }
  function waitingMirror(id,code,u) {
   let path=/databases/$(database)/documents/waitingStock/$(id)/waitingUnits/$(code);
   return waitingVacant(u)?existsAfter(path) && getAfter(path).data==waitingStockData(id,code,u):!existsAfter(path);
  }
  match /waitingStock/{id} {
   allow read: if workUser();
   allow create,update: if branchEdit(id) && request.resource.data=={'initialized':true};
   allow delete: if false;
   match /waitingUnits/{code} {
    allow create,update: if branchEdit(id)
     && existsAfter(/databases/$(database)/documents/branches/$(id)/units/$(code))
     && waitingVacant(getAfter(/databases/$(database)/documents/branches/$(id)/units/$(code)).data)
     && request.resource.data==waitingStockData(id,code,getAfter(/databases/$(database)/documents/branches/$(id)/units/$(code)).data);
    allow delete: if branchEdit(id) && (!existsAfter(/databases/$(database)/documents/branches/$(id)/units/$(code)) || !waitingVacant(getAfter(/databases/$(database)/documents/branches/$(id)/units/$(code)).data));
   }
  }
  match /{path=**}/waitingUnits/{code} { allow read: if workUser(); }
'''

FILES = {
    'src/WaitingList.tsx': r'''
import {useEffect,useState} from 'react';
import {X,Plus} from 'lucide-react';
import SearchInput from './SearchInput';
import {useWorkBranches} from './work-branches';
import {useWaitingList,saveWaiting,deleteWaiting,WaitingRow as Row} from './waiting-list';
import {taipeiDate} from './domain.js';
import {matchingVacancies} from './waiting-domain.js';
import './waiting-list.css';

const labels:Row={waiting:'候補中',rented:'已承租',cancelled:'已取消'};
const span=(lo:any,hi:any,suffix='')=>lo==null&&hi==null?'不限':`${lo??'不限'} ～ ${hi??'不限'}${suffix}`;
const blank=()=>({date:taipeiDate(),name:'',phone:'',email:'',volumeMin:'',volumeMax:'',priceMin:'',priceMax:'',needed:'',items:'',note:'',branchIds:[],otherBranches:'',status:'waiting'});
export type WaitingState=ReturnType<typeof useWaitingList>;

export default function WaitingList({profile,branches,branchId,state,focus,onFocus}: {
 profile:Row;
 branches:Row[];
 branchId:string;
 state:WaitingState;
 focus:string|null;
 onFocus:(id:string|null)=>void;
}){
 const [pendingStatus,setPendingStatus]=useState<Record<string,string>>({});
 const [unitFilter,setUnitFilter]=useState<string[]|null>(null);
 const directory=useWorkBranches(profile,branches);
 const [filter,setFilter]=useState('waiting');
 const [search,setSearch]=useState('');
 const [selected,setSelected]=useState<string|null>(null);
 const [edit,setEdit]=useState<Row|null>(null);
 const [other,setOther]=useState(false);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');

 const names=new Map(directory.branches.map(b=>[b.id,b.name]));
 const branchText=(r:Row)=>[
  ...r.branchIds.map((id:string)=>names.get(id)||branches.find(b=>b.id===id)?.name||'據點名稱載入中'),
  r.otherBranches?`其它：${r.otherBranches}`:''
 ].filter(Boolean).join('、');

 const open=(r:Row)=>{
  setSelected(r.id);
  setError('');
  void state.markRead(r);
 };

 useEffect(()=>{
  if(focus&&state.ready){
   if(focus.startsWith('unit:')){
    setUnitFilter(JSON.parse(focus.slice(5)));
    setSelected(null);
    setFilter('waiting');
    onFocus(null);
    return;
   }
   const row=state.rows.find(r=>r.id===focus);
   if(row){
    setSelected(row.id);
    setFilter('all');
    void state.markRead(row);
   }
   onFocus(null);
  }
 },[focus,state.ready]);

 const originalRow=state.rows.find(r=>r.id===selected);
 const row:Row|undefined=originalRow
  ?{...originalRow,status:pendingStatus[originalRow.id]??originalRow.status}
  :undefined;

 useEffect(()=>{
  if(originalRow&&pendingStatus[originalRow.id]===originalRow.status){
   setPendingStatus(v=>{
    const n={...v};
    delete n[originalRow.id];
    return n;
   });
  }
 },[originalRow?.id,originalRow?.status]);

 useEffect(()=>{
  if(originalRow&&state.ready)void state.markRead(originalRow);
 },[selected,Boolean(originalRow),state.ready]);

 const focusedUnit=unitFilter
  ?state.stock.find(u=>u.branchId===unitFilter[0]&&u.code===unitFilter[1])
  :null;

 const list=state.rows.filter(r=>
  (!unitFilter||(focusedUnit&&matchingVacancies(r,[focusedUnit]).length>0))
  &&(filter==='all'||r.status===filter)
  &&(branchId==='all'||r.branchIds.includes(branchId))
  &&[r.name,r.phone,r.email,r.items,r.note,branchText(r)].join(' ').toLowerCase().includes(search.trim().toLowerCase())
 );

 const startEdit=(r?:Row)=>{
  setError('');
  setEdit(r?{...r}:blank());
  setOther(!!r?.otherBranches);
 };
 const update=(key:string,value:any)=>setEdit(e=>e?{...e,[key]:value}:e);

 async function save(e:React.FormEvent){
  e.preventDefault();
  if(!edit||busy)return;
  setBusy(true);
  setError('');
  try{
   const id=await saveWaiting(
    {...edit,otherBranches:other?edit.otherBranches:''},
    edit.id,
    edit.revision
   );
   setEdit(null);
   setSelected(id);
  }catch(e:any){
   setError(e.message);
  }finally{
   setBusy(false);
  }
 }

 async function status(r:Row,next:string){
  if(busy)return;
  setPendingStatus(v=>({...v,[r.id]:next}));
  setBusy(true);
  setError('');
  try{
   await saveWaiting({...r,status:next},r.id,r.revision);
  }catch(e:any){
   setPendingStatus(v=>{
    const n={...v};
    delete n[r.id];
    return n;
   });
   setError(e.message);
  }finally{
   setBusy(false);
  }
 }

 async function remove(r:Row){
  if(!window.confirm(`確定刪除「${r.name}」的候補紀錄？刪除後無法還原。`))return;
  setBusy(true);
  setError('');
  try{
   await deleteWaiting(r);
   setSelected(null);
  }catch(e:any){
   setError(e.message);
  }finally{
   setBusy(false);
  }
 }

 return <>
  {(state.error||state.syncError||directory.error)&&
   <div role="alert" className="alert error">
    {state.error||state.syncError||directory.error}
    {state.syncError&&<button onClick={state.retrySync}>重試空倉同步</button>}
   </div>
  }
  {error&&!edit&&<div role="alert" className="alert error">{error}</div>}

  <div className="toolbar">
   <div className="waiting-status-tabs">
    {['waiting','rented','cancelled','all'].map(s=>
     <button key={s} className={filter===s?'primary':'secondary'} onClick={()=>setFilter(s)}>
      {labels[s]||'全部'}
     </button>
    )}
   </div>
   <button className="primary" onClick={()=>startEdit()}>
    <Plus size={16}/>新增候補
   </button>
  </div>

  <div className="toolbar">
   <div className="search">
    <SearchInput
     aria-label="搜尋候補"
     placeholder="搜尋姓名、電話前四碼、物品或備註"
     value={search}
     onChange={e=>setSearch(e.target.value)}
     onClear={()=>setSearch('')}
    />
   </div>
   <span className="hint">
    {state.syncing?'正在建立既有空倉索引…':`共 ${list.length} 筆`} · 需求金額以月租比對
   </span>
  </div>

  {unitFilter&&
   <div className="alert success">
    僅顯示符合空倉 {unitFilter[1]} 的候補
    <button onClick={()=>setUnitFilter(null)}>顯示全部候補</button>
   </div>
  }

  <section className="panel">
   <div className="table-wrap">
    <table>
     <thead>
      <tr>
       <th>登記日期</th><th>姓名</th><th>候補據點</th><th>需求材積</th>
       <th>需求月租</th><th>需求時間</th><th>合適空倉</th><th>狀態</th>
      </tr>
     </thead>
     <tbody>
      {list.map(r=><tr key={r.id}>
       <td>{r.date}</td>
       <td>
        <button className="text-button waiting-name" onClick={()=>open(r)}>
         {r.name}
         {state.unread(r)&&<i className="dot" aria-label="有新的合適空倉"/>}
        </button>
       </td>
       <td>{branchText(r)}</td>
       <td>{span(r.volumeMin,r.volumeMax)}</td>
       <td>{span(r.priceMin,r.priceMax,' 元')}</td>
       <td>{r.needed||''}</td>
       <td>
        <button className="text-button" onClick={()=>open(r)}>
         {r.status==='waiting'
          ?(state.ready?`${state.matches[r.id]?.length||0} 間`:'載入中…')
          :''}
        </button>
       </td>
       <td>{labels[r.status]}</td>
      </tr>)}
     </tbody>
    </table>
   </div>
   {state.ready&&!list.length&&<p className="empty">沒有符合的候補紀錄。</p>}
   {!state.ready&&!state.error&&<p role="status">載入候補清單中…</p>}
  </section>

  {row&&!edit&&
   <div className="modal-backdrop">
    <section className="modal wide" role="dialog" aria-modal="true" aria-label="候補明細">
     <div className="modal-heading">
      <h2>{row.name}・候補明細</h2>
      <button aria-label="關閉" onClick={()=>setSelected(null)}><X size={20}/></button>
     </div>
     <dl className="waiting-details">
      {[
       ['登記日期',row.date],['候補據點',branchText(row)],
       ['電話前四碼',row.phone],['Email',row.email],
       ['需求材積',span(row.volumeMin,row.volumeMax)],
       ['需求月租',span(row.priceMin,row.priceMax,' 元')],
       ['需求時間',row.needed],['存放物品',row.items],['備註',row.note]
      ].map(([k,v])=><div key={k}><dt>{k}</dt><dd>{v||''}</dd></div>)}
     </dl>

     <div className="waiting-status-tabs">
      <label>
       <input type="checkbox" checked={row.status==='rented'} disabled={busy}
        onChange={e=>status(row,e.target.checked?'rented':'waiting')}/>
       已承租
      </label>
      <label>
       <input type="checkbox" checked={row.status==='cancelled'} disabled={busy}
        onChange={e=>status(row,e.target.checked?'cancelled':'waiting')}/>
       已取消
      </label>
     </div>

     <h3>合適空倉</h3>
     {row.status!=='waiting'
      ?<p>這筆紀錄已停止配對。</p>
      :<>
       <p className="hint">
        依材積與月租範圍比對；需求時間供店長確認，不保證預留至該日期。
       </p>
       <div className="table-wrap">
        <table>
         <thead><tr><th>據點</th><th>倉號</th><th>材積</th><th>月租</th></tr></thead>
         <tbody>
          {(state.matches[row.id]||[]).map((u:Row)=>
           <tr key={u.branchId+'/'+u.code}>
            <td>{names.get(u.branchId)||u.branchId}</td>
            <td>{u.code}</td><td>{u.volume}</td>
            <td>NT$ {u.price.toLocaleString('zh-TW')}</td>
           </tr>
          )}
         </tbody>
        </table>
       </div>
       {!state.matches[row.id]?.length&&
        <p>目前沒有符合的空倉；其它據點僅記錄，不自動配對。</p>
       }
      </>
     }
     <div className="toolbar">
      <button className="secondary" disabled={busy} onClick={()=>startEdit(row)}>編輯</button>
      <button className="text-button danger" disabled={busy} onClick={()=>remove(row)}>刪除</button>
     </div>
    </section>
   </div>
  }

  {edit&&
   <div className="modal-backdrop">
    <section className="modal wide" role="dialog" aria-modal="true"
     aria-label={edit.id?'編輯候補':'新增候補'}>
     <div className="modal-heading">
      <h2>{edit.id?'編輯候補':'新增候補'}</h2>
      <button aria-label="關閉" disabled={busy} onClick={()=>setEdit(null)}><X size={20}/></button>
     </div>
     <form onSubmit={save}>
      <fieldset disabled={busy} className="waiting-form">
       <div className="waiting-fields">
        <label>
         登記日期
         <input type="date" required value={edit.date} onChange={e=>update('date',e.target.value)}/>
        </label>
        <label>
         姓名
         <input required maxLength={80} value={edit.name} onChange={e=>update('name',e.target.value)}/>
        </label>
        <label>
         電話前四碼（選填）
         <input inputMode="numeric" maxLength={4} pattern="[0-9]{1,4}" autoComplete="off"
          value={edit.phone}
          onChange={e=>update('phone',e.target.value.replace(/\D/g,'').slice(0,4))}/>
        </label>
        <label>
         Email（選填）
         <input type="email" maxLength={254} value={edit.email}
          onChange={e=>update('email',e.target.value)}/>
        </label>
       </div>

       <fieldset className="waiting-branches">
        <legend>候補據點（可複選）</legend>
        <div className="waiting-branch-grid">
         {directory.branches.map(b=>
          <label key={b.id}>
           <input type="checkbox" checked={edit.branchIds.includes(b.id)}
            onChange={e=>update('branchIds',e.target.checked
             ?[...edit.branchIds,b.id]
             :edit.branchIds.filter((id:string)=>id!==b.id))}/>
           <span>{b.name}</span>
          </label>
         )}
         <label>
          <input type="checkbox" checked={other} onChange={e=>setOther(e.target.checked)}/>
          <span>其它據點</span>
         </label>
        </div>
        {other&&
         <label>
          其它據點名稱
          <input required maxLength={300} placeholder="多個據點可用頓號分隔"
           value={edit.otherBranches} onChange={e=>update('otherBranches',e.target.value)}/>
         </label>
        }
       </fieldset>

       <div className="waiting-fields">
        {[
         ['需求材積','volumeMin','volumeMax'],
         ['需求月租金額（元）','priceMin','priceMax']
        ].map(([label,lo,hi])=>
         <fieldset className="waiting-range" key={lo}>
          <legend>{label}（選填）</legend>
          <div>
           <input aria-label={label+'下限'} type="number" min="0" max="100000000"
            step="any" placeholder="下限" value={edit[lo]??''}
            onChange={e=>update(lo,e.target.value)}/>
           <span>～</span>
           <input aria-label={label+'上限'} type="number" min="0" max="100000000"
            step="any" placeholder="上限" value={edit[hi]??''}
            onChange={e=>update(hi,e.target.value)}/>
          </div>
         </fieldset>
        )}
       </div>

       <p className="hint">上下限都不填代表不限；只填一邊也可以。範圍包含上下限。</p>
       <label>
        需求時間（選填）
        <input placeholder="MM/DD，例如 10/25" maxLength={5} value={edit.needed}
         onChange={e=>update('needed',e.target.value)}/>
       </label>
       <label>
        存放物品
        <textarea required maxLength={500} value={edit.items}
         onChange={e=>update('items',e.target.value)}/>
       </label>
       <label>
        備註（選填）
        <textarea maxLength={1000} value={edit.note}
         onChange={e=>update('note',e.target.value)}/>
       </label>
      </fieldset>
      {error&&<p role="alert" className="alert error">{error}</p>}
      <button className="primary" disabled={busy||!directory.ready}>
       {busy?'儲存中…':'確認儲存'}
      </button>
     </form>
    </section>
   </div>
  }
 </>;
}
'''.lstrip('\n'),

    'src/waiting-list.ts': r'''
import {useEffect,useMemo,useState} from 'react';
import {collection,collectionGroup,doc,onSnapshot,query,where,or,getDocs,getDoc,setDoc,writeBatch,serverTimestamp,runTransaction} from 'firebase/firestore';
import {auth,db} from './firebase';
import {matchingVacancies,vacancyKey,waitingInput} from './waiting-domain.js';
import {stockData} from './waiting-stock';

export type WaitingRow=Record<string,any>;
const message=(e:any)=>e.code==='permission-denied'
 ?'候補清單權限遭拒，請先發布最新 Firebase 規則後重新整理。'
 :e.message||'操作失敗';

export function useWaitingList(profile:WaitingRow|null,branches:WaitingRow[],initialize:boolean){
 const [archived,setArchived]=useState<string[]>([]);
 const [rows,setRows]=useState<WaitingRow[]>([]);
 const [stock,setStock]=useState<WaitingRow[]>([]);
 const [reads,setReads]=useState<Record<string,string[]>>({});
 const [error,setError]=useState('');
 const [syncError,setSyncError]=useState('');
 const [ready,setReady]=useState(false);
 const [syncing,setSyncing]=useState(false);
 const [retry,setRetry]=useState(0);

 const uid=auth.currentUser?.uid;
 const enabled=!!uid&&['admin','supervisor','manager'].includes(profile?.role);
 const global=profile&&['admin','supervisor'].includes(profile.role);
 const scope=JSON.stringify([uid,profile?.role,profile?.branchIds||[]]);

 useEffect(()=>{
  setRows([]);
  setStock([]);
  setArchived([]);
  setReads({});
  setError('');
  setReady(false);
  if(!enabled)return;

  const groups:WaitingRow[][]=[];
  let listReady=false,stockReady=false,readsReady=false;
  const seen=new Set<number>();
  const updateReady=()=>setReady(listReady&&stockReady&&readsReady);
  const stops:(()=>void)[]=[];
  const ids=profile?.branchIds||[];

  const sources=global
   ?[collection(db,'waitingList')]
   :Array.from({length:Math.max(1,Math.ceil(ids.length/29))},(_,i)=>{
     const group=ids.slice(i*29,i*29+29);
     return group.length
      ?query(collection(db,'waitingList'),or(
        where('createdBy','==',uid),
        where('branchIds','array-contains-any',group)
       ))
      :query(collection(db,'waitingList'),where('createdBy','==',uid));
    });

  const fail=(e:any)=>{
   setError(message(e));
   setReady(false);
  };

  sources.forEach((q,i)=>stops.push(onSnapshot(q,s=>{
   groups[i]=s.docs.map(d=>({id:d.id,...d.data()}));
   setRows([...new Map(groups.flat().map(r=>[r.id,r])).values()]
    .sort((a,b)=>b.date.localeCompare(a.date)||b.id.localeCompare(a.id)));
   seen.add(i);
   listReady=seen.size===sources.length;
   updateReady();
  },fail)));

  stops.push(onSnapshot(collection(db,'workBranches'),s=>{
   setArchived(s.docs.filter(d=>d.data().archived).map(d=>d.id));
  },fail));

  stops.push(onSnapshot(collectionGroup(db,'waitingUnits'),s=>{
   setStock(s.docs.map(d=>d.data()));
   stockReady=true;
   updateReady();
  },fail));

  stops.push(onSnapshot(collection(db,'waitingReads',uid!,'items'),s=>{
   setReads(Object.fromEntries(s.docs.map(d=>[d.id,d.data().seen||[]])));
   readsReady=true;
   updateReady();
  },fail));

  return()=>stops.forEach(stop=>stop());
 },[scope]);

 const branchScope=JSON.stringify(
  branches.filter(b=>!b.archived&&!b.importing).map(b=>b.id).sort()
 );

 useEffect(()=>{
  if(!enabled||!initialize)return;
  let active=true;
  setSyncing(true);
  setSyncError('');

  (async()=>{
   for(const id of JSON.parse(branchScope)){
    const marker=doc(db,'waitingStock',id);
    if((await getDoc(marker)).data()?.initialized)continue;

    const source=await getDocs(query(
     collection(db,'branches',id,'units'),
     where('status','==','vacant')
    ));
    const old=await getDocs(collection(marker,'waitingUnits'));
    const desired=new Map<string,WaitingRow>();

    for(const s of source.docs){
     const u=stockData(s.ref.path,s.data());
     if(u)desired.set(s.id,u);
    }

    const changes=[...desired.entries()]
     .map(([code,data])=>({ref:doc(marker,'waitingUnits',code),data}))
     .concat(old.docs.filter(d=>!desired.has(d.id))
      .map(d=>({ref:d.ref,data:null as any})));

    for(let i=0;i<changes.length;i+=8){
     const batch=writeBatch(db);
     for(const change of changes.slice(i,i+8)){
      if(change.data)batch.set(change.ref,change.data);
      else batch.delete(change.ref);
     }
     await batch.commit();
    }

    await setDoc(marker,{initialized:true});
   }
  })()
   .catch(e=>{if(active)setSyncError(message(e));})
   .finally(()=>{if(active)setSyncing(false);});

  return()=>{active=false;};
 },[scope,branchScope,initialize,retry]);

 const blocked=JSON.stringify([
  ...archived,
  ...branches.filter(b=>b.importing).map(b=>b.id)
 ].sort());

 const availableStock=useMemo(
  ()=>stock.filter(u=>!JSON.parse(blocked).includes(u.branchId)),
  [stock,blocked]
 );

 const matches=useMemo(
  ()=>Object.fromEntries(rows.map(r=>[r.id,matchingVacancies(r,availableStock)])),
  [rows,availableStock]
 );

 const unread=(row:WaitingRow)=>ready&&
  (matches[row.id]||[]).some((u:WaitingRow)=>
   !(reads[row.id]||[]).includes(vacancyKey(u))
  );

 async function markRead(row:WaitingRow){
  if(!uid||!ready)return;
  const keys=(matches[row.id]||[]).map(vacancyKey);
  if(!keys.length)return;

  const ref=doc(db,'waitingReads',uid,'items',row.id);
  try{
   await runTransaction(db,async tx=>{
    const old=await tx.get(ref);
    const seen=[...new Set([...(old.data()?.seen||[]),...keys])].slice(-2000);
    tx.set(ref,{seen});
   });
  }catch(e){
   setError(message(e));
  }
 }

 return {
  rows,stock:availableStock,matches,unread,
  hasUnread:rows.some(unread),markRead,ready,error,syncError,syncing,
  retrySync:()=>setRetry(n=>n+1)
 };
}

export async function saveWaiting(raw:WaitingRow,id?:string,revision?:number){
 const uid=auth.currentUser?.uid;
 if(!uid)throw new Error('請先登入');

 const clean=waitingInput(raw);
 const ref=id?doc(db,'waitingList',id):doc(collection(db,'waitingList'));

 await runTransaction(db,async tx=>{
  const old=await tx.get(ref);
  if(id&&(!old.exists()||old.data().revision!==revision)){
   throw new Error('這筆候補已被修改或刪除，請關閉後重新開啟');
  }
  const stamp=serverTimestamp();
  tx.set(ref,{
   ...clean,
   createdBy:old.data()?.createdBy||uid,
   createdAt:old.data()?.createdAt||stamp,
   updatedBy:uid,
   updatedAt:stamp,
   revision:(old.data()?.revision||0)+1
  });
 });
 return ref.id;
}

export async function deleteWaiting(row:WaitingRow){
 const ref=doc(db,'waitingList',row.id);
 await runTransaction(db,async tx=>{
  const s=await tx.get(ref);
  if(!s.exists())return;
  if(s.data().revision!==row.revision){
   throw new Error('資料已被修改，請重新確認後刪除');
  }
  tx.delete(ref);
 });
}
'''.lstrip('\n'),

    'src/waiting-stock.ts': r'''
import {doc,runTransaction as originalTransaction,writeBatch as originalBatch} from 'firebase/firestore';
import type {Firestore,Transaction,TransactionOptions,WriteBatch} from 'firebase/firestore';

type Row=Record<string,any>;
export const unitPath=(path:string)=>/^branches\/[^/]+\/units\/[^/]+$/.test(path);

export function stockRef(db:Firestore,path:string){
 const p=path.split('/');
 return doc(db,'waitingStock',p[1],'waitingUnits',p[3]);
}

export function stockData(path:string,u:Row|null){
 if(!u||u.status!=='vacant'||u.missing||u.archived)return null;
 const p=path.split('/');
 return {
  branchId:p[1],
  code:p[3],
  volume:u.volume,
  price:u.price,
  vacantSince:u.vacantSince??null,
  lastEventId:u.lastEventId??null,
  lastEventDate:u.lastEventDate??null
 };
}

export function runTransaction<T>(
 db:Firestore,
 fn:(t:Transaction)=>Promise<T>,
 options?:TransactionOptions
):Promise<T>{
 return originalTransaction(db,async original=>{
  const cache=new Map<string,Row|null>();
  const writes:{method:string;args:any[]}[]=[];

  const wrapped=new Proxy(original,{
   get(target,key){
    if(key==='get'){
     return async(ref:any)=>{
      const s=await original.get(ref);
      cache.set(ref.path,s.exists()?s.data() as Row:null);
      return s;
     };
    }
    if(['set','update','delete'].includes(String(key))){
     return(...args:any[])=>{
      writes.push({method:String(key),args});
      return wrapped;
     };
    }
    const value=(target as any)[key];
    return typeof value==='function'?value.bind(target):value;
   }
  }) as Transaction;

  const result=await fn(wrapped);

  for(const w of writes){
   if(unitPath(w.args[0].path)&&!cache.has(w.args[0].path)){
    const s=await original.get(w.args[0]);
    cache.set(w.args[0].path,s.exists()?s.data() as Row:null);
   }
  }

  const touched=new Set<string>();
  for(const w of writes){
   (original as any)[w.method](...w.args);
   const path=w.args[0].path;
   if(!unitPath(path))continue;

   touched.add(path);
   const old=cache.get(path);
   if(w.method==='delete')cache.set(path,null);
   else if(w.method==='update'||w.args[2]?.merge){
    cache.set(path,{...old,...w.args[1]});
   }else{
    cache.set(path,w.args[1]);
   }
  }

  for(const path of touched){
   const data=stockData(path,cache.get(path)||null);
   const ref=stockRef(db,path);
   if(data)original.set(ref,data);
   else original.delete(ref);
  }
  return result;
 },options);
}

export function writeBatch(db:Firestore):WriteBatch{
 const original=originalBatch(db);
 const wrapped=new Proxy(original,{
  get(target,key){
   if(['set','update','delete'].includes(String(key))){
    return(...args:any[])=>{
     (original as any)[key](...args);

     if(unitPath(args[0].path)){
      const u=args[1];
      if(key==='update'&&!u?.archived&&!u?.missing){
       throw new Error('倉位部分更新請使用交易');
      }
      const data=key==='delete'||key==='update'
       ?null
       :stockData(args[0].path,u);

      if(data)original.set(stockRef(db,args[0].path),data);
      else original.delete(stockRef(db,args[0].path));
     }
     return wrapped;
    };
   }
   const value=(target as any)[key];
   return typeof value==='function'?value.bind(target):value;
  }
 }) as WriteBatch;
 return wrapped;
}
'''.lstrip('\n'),

    'src/waiting-domain.js': r'''
export const waitingStatuses = ['waiting','rented','cancelled'];

export function waitingInput(raw) {
  const text = (key, max, required=false) => {
    const value = String(raw[key] ?? '').trim();
    if ((required && !value) || value.length > max) {
      throw new Error(`${key === 'name' ? '姓名' : key === 'items' ? '存放物品' : key}未填寫或過長`);
    }
    return value;
  };

  const number = key => {
    if (raw[key] == null || String(raw[key]).trim() === '') return null;
    const n = Number(raw[key]);
    if (!Number.isFinite(n) || n < 0 || n > 100000000) {
      throw new Error('需求範圍請輸入有效的非負數字');
    }
    return n;
  };

  const phone=text('phone',4);
  const email=text('email',254);
  const needed=text('needed',5);

  if (phone && !/^\d{1,4}$/.test(phone)) {
    throw new Error('電話只能輸入前四碼，最多 4 位數字');
  }
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    throw new Error('Email 格式不正確');
  }
  if (needed) {
    const m=needed.match(/^(\d{2})\/(\d{2})$/);
    if (
      !m || +m[1]<1 || +m[1]>12 || +m[2]<1 ||
      +m[2]>[31,29,31,30,31,30,31,31,30,31,30,31][+m[1]-1]
    ) {
      throw new Error('需求時間請輸入有效的 MM/DD');
    }
  }

  const date=text('date',10,true);
  if (
    !/^20\d{2}-\d{2}-\d{2}$/.test(date) ||
    new Date(date+'T00:00:00Z').toISOString().slice(0,10)!==date
  ) {
    throw new Error('登記日期不正確');
  }

  const branchIds=[...new Set(raw.branchIds || [])];
  if (
    branchIds.length>100 ||
    branchIds.some(id=>typeof id!=='string'||!id||id.includes('/'))
  ) {
    throw new Error('候補據點不正確');
  }

  const otherBranches=text('otherBranches',300);
  if (!branchIds.length&&!otherBranches) {
    throw new Error('請選擇候補據點，或填寫其它據點');
  }

  const result={
    date,
    name:text('name',80,true),
    phone,
    email,
    needed,
    items:text('items',500,true),
    note:text('note',1000),
    branchIds,
    otherBranches,
    volumeMin:number('volumeMin'),
    volumeMax:number('volumeMax'),
    priceMin:number('priceMin'),
    priceMax:number('priceMax'),
    status:raw.status || 'waiting'
  };

  if (!waitingStatuses.includes(result.status)) {
    throw new Error('候補狀態不正確');
  }
  for(const [lo,hi]of[
    ['volumeMin','volumeMax'],
    ['priceMin','priceMax']
  ]) {
    if(result[lo]!==null&&result[hi]!==null&&result[lo]>result[hi]) {
      throw new Error('需求範圍下限不可大於上限');
    }
  }
  return result;
}

export function matchingVacancies(row, vacancies) {
  if(row.status!=='waiting') return [];
  return vacancies.filter(u=>
    row.branchIds.includes(u.branchId)&&
    ['volume','price'].every(k=>{
      const n=u[k], min=row[k+'Min'], max=row[k+'Max'];
      return typeof n==='number'&&Number.isFinite(n)&&
        (min==null||n>=min)&&(max==null||n<=max);
    })
  );
}

export function vacancyKey(u) {
  return JSON.stringify([
    u.branchId,u.code,u.vacantSince,u.lastEventId,u.lastEventDate
  ]);
}
'''.lstrip('\n'),

    'src/waiting-list.css': r'''
.waiting-status-tabs {
  display:flex;
  gap:10px;
  flex-wrap:wrap;
  align-items:center;
}
.waiting-status-tabs label,
.waiting-branch-grid label {
  display:flex!important;
  flex-direction:row!important;
  align-items:center;
  gap:10px;
  margin:0;
}
.waiting-status-tabs input,
.waiting-branch-grid input {
  width:18px!important;
  height:18px;
  flex:0 0 18px;
}
.waiting-fields {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:16px;
}
.waiting-fields label { min-width:0; }
.waiting-form {
  border:0;
  padding:0;
  margin:0;
  min-width:0;
}
.waiting-form > label { margin-top:16px; }
.waiting-range {
  min-width:0;
  border:1px solid #dae3ed;
  border-radius:8px;
  padding:12px;
}
.waiting-range > div {
  display:flex;
  gap:8px;
  align-items:center;
}
.waiting-range input {
  min-width:0;
  width:100%;
}
.waiting-branches { margin:18px 0; }
.waiting-branch-grid {
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
  gap:10px;
  max-height:220px;
  overflow:auto;
  padding:6px;
}
.waiting-branch-grid label {
  border:1px solid #dae3ed;
  border-radius:8px;
  padding:10px;
}
.waiting-branch-grid span { overflow-wrap:anywhere; }
.waiting-name {
  display:inline-flex;
  gap:8px;
  align-items:center;
}
.waiting-name .dot {
  position:static;
  flex-shrink:0;
}
.waiting-details {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:16px;
}
.waiting-details dt {
  color:#77869e;
  font-size:13px;
}
.waiting-details dd {
  margin:5px 0 0;
  white-space:pre-wrap;
  overflow-wrap:anywhere;
}
.waiting-unit-match {
  display:block;
  font-size:12px;
  margin-top:6px;
}
@media(max-width:600px){
  .waiting-fields,
  .waiting-details {
    grid-template-columns:1fr;
  }
}
'''.lstrip('\n'),

    'src/OccupancyChart.tsx': r'''
import './occupancy-chart.css';

function offset(month:string,n:number){
 const [y,m]=month.split('-').map(Number);
 return new Date(Date.UTC(y,m-1+n,1)).toISOString().slice(0,7);
}

export default function OccupancyChart({month,rateFor}:{
 month:string;
 rateFor:(m:string)=>number|null;
}){
 return (
  <div className="occupancy-chart-scroll">
   <div className="occupancy-chart" role="img"
    aria-label="最近六個月出租率與去年同期比較">
    {Array.from({length:6},(_,i)=>offset(month,i-5)).map(m=>
     <div className="occupancy-month" key={m}>
      <div className="occupancy-pair">
       {[m,offset(m,-12)].map((period,index)=>{
        const rate=rateFor(period);
        return (
         <div className="occupancy-series" key={period}
          title={`${period}：${rate===null?'無資料':rate.toFixed(1)+'%'}`}>
          <span>{rate===null?'無資料':rate.toFixed(1)+'%'}</span>
          <div className="occupancy-track">
           {rate!==null&&
            <div className={index?'occupancy-bar previous':'occupancy-bar current'}
             style={{height:Math.max(0,Math.min(100,rate))+'%'}}/>
           }
          </div>
         </div>
        );
       })}
      </div>
      <small>{m.slice(0,4)}/{m.slice(5)}</small>
     </div>
    )}
   </div>
  </div>
 );
}
'''.lstrip('\n'),

    'src/occupancy-chart.css': r'''
.occupancy-chart-scroll {
  overflow-x:auto;
  padding:0 24px 18px;
}
.occupancy-chart {
  display:flex;
  gap:16px;
  min-width:510px;
}
.occupancy-month {
  flex:1;
  text-align:center;
  min-width:64px;
}
.occupancy-pair {
  display:flex;
  gap:5px;
  justify-content:center;
}
.occupancy-series {
  flex:1;
  max-width:46px;
  min-width:29px;
}
.occupancy-series > span {
  display:block;
  color:#718099;
  font-size:11px;
  margin-bottom:6px;
  white-space:nowrap;
}
.occupancy-track {
  display:flex;
  height:150px;
  align-items:flex-end;
  background:repeating-linear-gradient(
    to top,transparent 0,transparent 36px,#f0f3f7 37px,transparent 38px
  );
}
.occupancy-bar {
  width:100%;
  border-radius:4px 4px 0 0;
}
.occupancy-bar.current { background:#204b80; }
.occupancy-bar.previous { background:#b5c8df; }
.occupancy-month > small {
  display:block;
  margin-top:10px;
  color:#718099;
  font-size:12px;
}
.occupancy-legend {
  display:flex;
  gap:12px;
  flex-wrap:wrap;
  font-size:13px;
  color:#718099;
}
.occupancy-legend span {
  display:inline-flex;
  align-items:center;
  gap:5px;
}
.occupancy-legend i {
  width:8px;
  height:8px;
  border-radius:2px;
  background:#204b80;
}
.occupancy-legend .previous { background:#b5c8df; }
.target-panel > .panel-heading { padding:0 0 16px; }
'''.lstrip('\n'),

    'src/manual-waiting.ts': r'''
import type {ManualPage,ManualTopic} from './manual-content';

export const waitingManual:ManualPage={
 id:'waiting',
 title:'候補清單',
 intro:'登記客人的候補條件，查看符合需求的空倉，並追蹤已承租或已取消狀態。',
 access:'店長：自己建立或候補據點包含所屬分店的紀錄；主管／管理員：全部紀錄',
 topics:[
  {
   title:'新增候補與選填欄位',
   steps:[
    '點「新增候補」，登記日期預設今天，可自行修改。',
    '填寫姓名、存放物品及候補據點；電話、Email、材積、金額、需求時間及備註可留白。',
    '電話只保留前四碼，最多輸入 4 位數字；不要把完整電話放入其它欄位。',
    '需求時間以 MM/DD 輸入，例如 10/25；此欄只供店長確認，不會預留空倉。'
   ],
   result:'按「確認儲存」後建立候補紀錄，不會新增租約或計入業績。'
  },
  {
   title:'材積、月租範圍與候補據點',
   steps:[
    '材積與月租金額各有下限、上限；例如材積填 80、120，包含 80 與 120。',
    '可只填上限或下限；兩格都不填代表不限。',
    '候補據點可複選網頁內所有據點；選「其它據點」後填名稱，多間可用頓號分隔。'
   ],
   result:'網頁內據點以空倉的材積及月租比對；其它據點只做紀錄，不自動配對。'
  },
  {
   title:'合適空倉、紅點與倉位管理提示',
   steps:[
    '系統顯示符合條件的空倉數量，點姓名或空倉數開啟候補明細。',
    '符合條件的新空倉會在側欄「候補清單」及該筆紀錄旁顯示紅點；點開該筆紀錄才標記自己的已讀。',
    '不同帳號的已讀互不影響；之後有新空倉符合，會再次提醒。',
    '在倉位管理看到「符合候補 N 筆」時，可點擊查看符合該空倉且有權限查看的名單。'
   ],
   result:'空倉索引只提供倉號、材積、月租及配對必要資訊，不開放其他分店的完整倉位資料。首次上線請主管或管理員開啟候補清單，建立所有既有空倉的索引；各店店長也能建立自己所屬據點索引。'
  },
  {
   title:'搜尋、編輯與完成狀態',
   steps:[
    '可切換「候補中」「已承租」「已取消」「全部」，並搜尋姓名、電話前四碼、物品或備註；搜尋框右側 × 可清空。',
    '點姓名開啟明細，再按「編輯」調整條件。',
    '「已承租」與「已取消」只能擇一；取消勾選後恢復候補中。'
   ],
   result:'已承租、已取消會停止配對及提醒；勾選已承租只更新候補狀態，實際租約仍需到倉位管理登記。'
  },
  {
   title:'刪除與共同編輯',
   steps:[
    '有權限的店長、主管或管理員可修改與刪除紀錄；跨店共同可見時，操作會同步。',
    '刪除前核對對象並確認，刪除後無法還原。',
    '若系統提示已被他人修改，關閉明細後重新開啟，再確認最新內容。'
   ],
   result:'刪除候補紀錄不會刪除倉位或租約，也不會改變 KPI。'
  }
 ]
};

export const waitingDashboardTopics:ManualTopic[]=[
 {
  title:'出租率與去年同期雙柱圖',
  steps:[
   '在出租率趨勢查看最近六個月，每月以深色本期、淺色去年同期並排呈現。',
   '柱上數字及月份可用來核對；缺少資料會顯示「無資料」，不當成零。',
   '手機可左右滑動圖表；跨年時會讀取足夠的同期歷史月份。'
  ],
  result:'圖表使用出租率，並非業績金額。'
 },
 {
  title:'收合概況與業績去年同月比較',
  steps:[
   '選全部據點時，「各據點營運概況」及其後的「業績去年同月比較」預設收合，點標題展開。',
   '選單一據點時直接顯示；單店業績表只列該店，不重複顯示合計。',
   '業績比較讀取已匯入 KPI 的實際業績，顯示本期、去年同月、增減金額及增減率；多店合計只納入兩年都有資料的店。'
  ],
  result:'去年業績為零時不計算增減百分比；缺資料不當成零。當月尚未結束時，與去年整月的比較不代表同期累計。'
 }
];

export const waitingUnitTopic:ManualTopic={
 title:'空倉的候補媒合提示',
 steps:[
  '空倉若符合目前帳號可查看的候補需求，狀態旁會顯示「符合候補 N 筆」。',
  '點提示後會開啟候補清單，只列符合這個空倉的候補；點「顯示全部候補」可解除限制。',
  '點開候補明細可查看需求並聯絡客人，確認後再到倉位管理辦理承租。'
 ],
 result:'僅計入候補中紀錄，已承租、已取消不計入；媒合提示不會自動保留倉位或建立租約。'
};
'''.lstrip('\n'),
}

root = Path(__file__).resolve().parents[1]
changes = {}


def read(name):
    return changes.get(name, (root / name).read_text(encoding='utf-8'))


def once(text, old, new):
    if text.count(old) != 1:
        raise SystemExit('版本不符，未修改檔案：' + old[:70])
    return text.replace(old, new, 1)


main = read('src/main.tsx')

if 'import WaitingList from' not in main:
    main = (
        'import WaitingList from "./WaitingList";\n'
        'import {useWaitingList} from "./waiting-list";\n'
        'import {matchingVacancies} from "./waiting-domain.js";\n'
        + main
    )
    main = once(
        main,
        'const work = useWorkTasks(profile);',
        'const work = useWorkTasks(profile);\n'
        '  const waiting = useWaitingList(profile,branches,page === "waiting" || page === "units");\n'
        '  const [waitingFocus,setWaitingFocus] = useState<string|null>(null);'
    )

    main, count = re.subn(
        r'(\["targets",\s*"目標與轉介",\s*LayoutDashboard\],)',
        r'\1\n    ...(canWrite ? [["waiting", "候補清單", Users]] : []),',
        main,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到側欄位置，未修改檔案')

    main = once(
        main,
        '{id === "work" && work.hasUnread',
        '{id === "waiting" && waiting.hasUnread && <i className="dot" aria-label="候補清單有合適空倉" />}\n'
        '              {id === "work" && work.hasUnread'
    )

    def skip(match):
        condition = match.group(1)
        if all(word in condition for word in ['"users"', '"work"', '"manual"']):
            return 'if (' + condition + ' || page === "waiting") return;'
        return match.group(0)

    main = re.sub(r'if\s*\(([^;\n]+)\)\s*return;', skip, main)
    if '|| page === "waiting") return;' not in main:
        raise SystemExit('找不到資料訂閱位置，未修改檔案')

    main = once(
        main,
        'page !== "work" &&',
        'page !== "work" && page !== "waiting" &&'
    )
    main = once(
        main,
        ': page === "work" ? "追蹤據點待辦',
        ': page === "waiting" ? "登記候補需求，追蹤符合材積與月租的空倉。" : page === "work" ? "追蹤據點待辦'
    )
    main = once(
        main,
        '{page === "manual" && <OperationManual/>}',
        '{page === "manual" && <OperationManual/>}\n'
        '              {page === "waiting" && canWrite && profile && <WaitingList profile={profile} branches={branches} branchId={branchId} state={waiting} focus={waitingFocus} onFocus={setWaitingFocus}/>}'
    )

    badge = re.search(
        r'<span\s+className=\{`badge \$\{leaseStatus\((\w+), currentDate\)\.color\}`\}[\s\S]*?</span>',
        main
    )
    if not badge:
        raise SystemExit('找不到倉位狀態欄，未修改檔案')

    button = '''{canWrite && !UNIT.missing && !UNIT.archived && UNIT.status==='vacant' && waiting.ready && (()=>{
      const matched=waiting.rows.filter(r=>matchingVacancies(r,[UNIT]).length>0);
      return matched.length>0?<button className="text-button waiting-unit-match" onClick={()=>{setWaitingFocus("unit:"+JSON.stringify([UNIT.branchId,UNIT.code]));setBranchId(UNIT.branchId);setPage('waiting');}}>符合候補 {matched.length} 筆</button>:null;
    })()}'''.replace('UNIT', badge.group(1))

    main = main[:badge.end()] + button + main[badge.end():]

if 'import OccupancyChart from' not in main:
    main = 'import OccupancyChart from "./OccupancyChart";\n' + main
    main = once(
        main,
        '`${Number(month.slice(0,4))-1}-01`',
        'monthOffset(month,-17)'
    )

    main, count = re.subn(
        r'<span className="legend">\s*<i /> 出租率\s*</span>',
        '<div className="occupancy-legend"><span><i/>本期</span><span><i className="previous"/>去年同期</span></div>',
        main,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到出租率圖例，未修改檔案')

    start = main.index('<div className="chart">')
    end = main.index('<div className="comparisons">', start)
    main = (
        main[:start]
        + '<OccupancyChart month={month} rateFor={m=>rate(stats(m))}/>\n                      '
        + main[end:]
    )

main = main.replace(
    '<BranchOverviewDisclosure key={branchId}',
    '<BranchOverviewDisclosure key={"overview-"+branchId}'
).replace(
    '<RevenueComparison key={branchId}',
    '<RevenueComparison key={"revenue-"+branchId}'
)
changes['src/main.tsx'] = main

for name in [
    'api.ts',
    'transfers.ts',
    'review-inventory.ts',
    'pending-renewals.ts',
    'manual-pending-renewal.ts',
    'import-actions.ts',
    'targets-api.ts'
]:
    path = 'src/' + name
    text = read(path)

    if 'from "./waiting-stock"' not in text:
        found = []

        def imports(match):
            body = match.group(1)
            for word in ['runTransaction', 'writeBatch']:
                if re.search(r'\b' + word + r'\b', body):
                    found.append(word)
                    body = re.sub(r'\b' + word + r'\s*,?', '', body)
            return (
                'import {' + body + '} from '
                + match.group(2) + 'firebase/firestore'
                + match.group(2) + ';'
            )

        text = re.sub(
            r'import\s*\{([^}]+)\}\s*from\s*([\'\"])firebase/firestore\2;',
            imports,
            text
        )
        if not found:
            raise SystemExit('找不到倉位寫入入口，未修改檔案：' + name)

        text = 'import {' + ','.join(found) + '} from "./waiting-stock";\n' + text

    if name in ['api.ts', 'import-actions.ts']:
        text = re.sub(r'(\+=|\+)\s*350\b', r'\1 8', text)

    changes[path] = text

revenue = read('src/RevenueComparison.tsx')
if 'showTotal: boolean' not in revenue:
    revenue, count = re.subn(
        r'function RevenueComparisonContent\([\s\S]*?\)\s*\{',
        'function RevenueComparisonContent({branches, data, month, showTotal}: {branches: Row[]; data: Record<string, Row>; month: string; showTotal: boolean}) {',
        revenue,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到業績比較元件，未修改檔案')

    revenue, count = re.subn(
        r'(<p>\s*可比較據點[\s\S]*?</p>)',
        r'{showTotal && \1}',
        revenue,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到業績合計說明，未修改檔案')

    revenue, count = re.subn(
        r'(<tr>\s*<th>可比較據點合計</th>[\s\S]*?</tr>)',
        r'{showTotal && \1}',
        revenue,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到業績合計列，未修改檔案')

    revenue = revenue.replace(
        '<RevenueComparisonContent {...props}/>',
        '<RevenueComparisonContent {...props} showTotal={collapsible}/>'
    )
changes['src/RevenueComparison.tsx'] = revenue

insights = read('src/LightInsights.tsx')
if 'operations-insights' not in insights:
    insights = once(
        insights,
        'className="panel target-panel"',
        'className="panel target-panel operations-insights"'
    )
changes['src/LightInsights.tsx'] = insights

style = read('src/style.css')
if '/* Consistent dashboard insight typography. */' not in style:
    style += '''
/* Consistent dashboard insight typography. */
.operations-insights h2 { font-size:20px; margin:0 0 12px; }
.operations-insights h3 { font-size:18px; }
.operations-insights > p:not(.hint) { font-size:16px; line-height:1.7; }
.operations-insights > .badge { font-size:14px; margin:4px 10px 4px 0; }
'''
changes['src/style.css'] = style

manual = read('src/manual-content.ts')
if '// waiting-list-manual-v1' not in manual:
    manual = (
        'import {waitingManual,waitingDashboardTopics,waitingUnitTopic} from "./manual-waiting";\n'
        + manual
    )
    manual += '''
// waiting-list-manual-v1
manualPages.splice(manualPages.findIndex(p=>p.id==='work'),0,waitingManual);
manualPages.find(p=>p.id==='dashboard')?.topics.push(...waitingDashboardTopics);
manualPages.find(p=>p.id==='units')?.topics.push(waitingUnitTopic);
'''
changes['src/manual-content.ts'] = manual

rules = read('firestore.rules')
if '// storeasy-waiting-list-v1' not in rules:
    rules, count = re.subn(
        r'(function validUnit\(\)\s*\{\s*let u\s*=\s*request.resource.data;\s*return)\s*',
        r'\1 waitingMirror(id,code,u) && ',
        rules,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到倉位規則，未修改檔案')

    rules, count = re.subn(
        r"(allow delete: if branchEdit\(id\)\s*&& unlocked\(id\)\s*&& resource.data.status\s*==\s*'vacant')\s*;",
        r'\1 && !existsAfter(/databases/$(database)/documents/waitingStock/$(id)/waitingUnits/$(code));',
        rules,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到倉位刪除規則，未修改檔案')

    rules, count = re.subn(
        r'match /\{document=\*\*\}\s*\{\s*allow read, write: if false;\s*\}',
        lambda m: WAITING_RULES + '\n' + m.group(0),
        rules,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到規則結尾，未修改檔案')
changes['firestore.rules'] = rules

agents = (
    (root / 'AGENTS.md').read_text(encoding='utf-8')
    if (root / 'AGENTS.md').exists()
    else '# 專案維護約定\n'
)
if '<!-- manual-maintenance -->' not in agents:
    agents += (
        '\n<!-- manual-maintenance -->\n'
        '每次新增、修改或移除使用者可見功能時，必須在同一筆更新同步維護操作手冊'
        '（src/manual-content.ts 及相關 manual 模組），核對按鈕名稱、權限、操作步驟與資料影響，'
        '並驗證手冊仍能正常顯示與搜尋。此為使用者要求。\n'
    )
changes['AGENTS.md'] = agents

changes.update(FILES)

for name, text in changes.items():
    path = root / name
    if path.exists():
        backup = root / '.update-backups' / 'waiting-list' / name
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_text(
                path.read_text(encoding='utf-8'),
                encoding='utf-8'
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')

print('已更新候補清單、倉位配對、同期圖表、排版與操作手冊')
print('請發布更新後的 firestore.rules，並由主管或管理員首次開啟候補清單建立既有空倉索引。')
