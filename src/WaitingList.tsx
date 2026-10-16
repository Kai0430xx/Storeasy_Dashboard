import WaitingBranchPicker from "./WaitingBranchPicker";
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
    <section className="modal wide waiting-editor" role="dialog" aria-modal="true"
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

       <WaitingBranchPicker
        key={edit.id || 'new'}
        branches={directory.branches}
        ownedIds={profile.branchIds || []}
        global={['admin','supervisor'].includes(profile.role)}
        selected={edit.branchIds}
        onChange={ids=>update('branchIds',ids)}
        other={other}
        onOtherChange={setOther}
        otherName={edit.otherBranches}
        onOtherNameChange={name=>update('otherBranches',name)}
       />

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
