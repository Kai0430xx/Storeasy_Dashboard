import WaitingBranches from "./WaitingBranches";
import WaitingMatches from "./WaitingMatches";
import {WaitingDateFields,WaitingStatus} from "./WaitingFields";
import WaitingNotes from "./WaitingNotes";
import {activeWaiting,displayWaitingDate,waitingStatusLabels} from "./waiting-domain.js";
import WaitingBranchPicker from "./WaitingBranchPicker";
import {useEffect,useState} from 'react';
import {X,Plus} from 'lucide-react';
import SearchInput from './SearchInput';
import {useWorkBranches} from './work-branches';
import {useWaitingList,saveWaiting,deleteWaiting,WaitingRow as Row} from './waiting-list';
import {taipeiDate} from './domain.js';
import {matchingVacancies} from './waiting-domain.js';
import './waiting-list.css';
const labels:Row=waitingStatusLabels;
const span=(lo:any,hi:any,suffix='')=>lo==null&&hi==null?'不限':`${lo??'不限'} ～ ${hi??'不限'}${suffix}`;
const blank=()=>({date:taipeiDate(),name:'',phone:'',email:'',volumeMin:'',volumeMax:'',priceMin:'',priceMax:'',needed:'',expires:'',noteDrafts:[],items:'',note:'',branchIds:[],otherBranches:'',status:'waiting'});
export type WaitingState=ReturnType<typeof useWaitingList>;
export default function WaitingList({profile,branches,branchId,state,focus,onFocus,onRent}: {profile:Row;branches:Row[];branchId:string;state:WaitingState;focus:string|null;onFocus:(id:string|null)=>void;onRent:(unit:Row)=>Promise<void>}){
 const [hasUnaddedNote,setHasUnaddedNote]=useState(false);
 const [pendingStatus,setPendingStatus]=useState<Record<string,string>>({});
 const [unitFilter,setUnitFilter]=useState<string[]|null>(null);
 const directory=useWorkBranches(profile,branches),[filter,setFilter]=useState('waiting'),[search,setSearch]=useState(''),[selected,setSelected]=useState<string|null>(null),[edit,setEdit]=useState<Row|null>(null),[other,setOther]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [savedNotice,setSavedNotice]=useState('');
 const names=new Map(directory.branches.map(b=>[b.id,b.name]));
 const branchText=(r:Row)=>[...r.branchIds.map((id:string)=>names.get(id)||branches.find(b=>b.id===id)?.name||'據點名稱載入中'),r.otherBranches?`其它：${r.otherBranches}`:''].filter(Boolean).join('、');
 const open=(r:Row)=>{setSavedNotice('');setSelected(r.id);setError('');void state.markRead(r);};
 useEffect(()=>{if(focus&&state.ready){if(focus.startsWith('unit:')){setUnitFilter(JSON.parse(focus.slice(5)));setSelected(null);setFilter('waiting');onFocus(null);return;}const row=state.rows.find(r=>r.id===focus);if(row){setSelected(row.id);setFilter('all');void state.markRead(row);}onFocus(null);}},[focus,state.ready]);
 const originalRow=state.rows.find(r=>r.id===selected);
 const row:Row|undefined=originalRow?{...originalRow,status:pendingStatus[originalRow.id]??originalRow.status}:undefined;
 useEffect(()=>{if(originalRow&&pendingStatus[originalRow.id]===originalRow.status)setPendingStatus(v=>{const n={...v};delete n[originalRow.id];return n;});},[originalRow?.id,originalRow?.status]);
 useEffect(()=>{if(originalRow&&state.ready)void state.markRead(originalRow);},[selected,Boolean(originalRow),state.ready]);
 const focusedUnit=unitFilter?state.stock.find(u=>u.branchId===unitFilter[0]&&u.code===unitFilter[1]):null;
 const list=state.rows.filter(r=>(!unitFilter||(focusedUnit&&matchingVacancies(r,[focusedUnit]).length>0))&&(r.deleting||filter==='all'||(filter==='waiting'?activeWaiting(r):r.status===filter))&&(branchId==='all'||r.branchIds.includes(branchId))&&[r.name,r.phone,r.email,r.items,r.note,branchText(r)].join(' ').toLowerCase().includes(search.trim().toLowerCase()));
 const startEdit=(r?:Row)=>{setSavedNotice('');setError('');setEdit(r?{...r,noteDrafts:[]}:blank());setOther(!!r?.otherBranches);};
 const update=(key:string,value:any)=>setEdit(e=>e?{...e,[key]:value}:e);
 async function save(e:React.FormEvent){e.preventDefault();if(!edit||busy)return;if(hasUnaddedNote){setError('請先按「加入備註」或「取消新增備註」，再確認儲存');return;}setBusy(true);setError('');try{await saveWaiting({...edit,otherBranches:other?edit.otherBranches:''},edit.id,edit.revision);setEdit(null);setSelected(null);setSavedNotice('候補已儲存');}catch(e:any){setError(e.message);}finally{setBusy(false);}}
 async function status(r:Row,next:string){if(busy)return;setPendingStatus(v=>({...v,[r.id]:next}));setBusy(true);setError('');try{await saveWaiting({...r,status:next},r.id,r.revision);}catch(e:any){setPendingStatus(v=>{const n={...v};delete n[r.id];return n;});setError(e.message);}finally{setBusy(false);}}
 async function remove(r:Row){if(!window.confirm(`確定刪除「${r.name}」的候補紀錄？刪除後無法還原。`))return;setBusy(true);setError('');try{await deleteWaiting(r);setSelected(null);}catch(e:any){setError(e.message);}finally{setBusy(false);}}
 return <>
  {savedNotice&&!edit&&<div className="alert success" role="status">{savedNotice}<button aria-label="關閉儲存提示" onClick={()=>setSavedNotice('')}>×</button></div>}
  {(state.error||state.syncError||directory.error)&&<div role="alert" className="alert error">{state.error||state.syncError||directory.error}{state.syncError&&<button onClick={state.retrySync}>重試空倉同步</button>}</div>}
  {error&&!edit&&<div role="alert" className="alert error">{error}</div>}
  <div className="toolbar"><div className="waiting-status-tabs">{['waiting','rented','cancelled','all'].map(s=><button key={s} className={filter===s?'primary':'secondary'} onClick={()=>setFilter(s)}>{s==='waiting'?'候補中':labels[s]||'全部'}</button>)}</div><button className="primary" onClick={()=>startEdit()}><Plus size={16}/>新增候補</button></div>
  <div className="toolbar"><div className="search"><SearchInput aria-label="搜尋候補" placeholder="搜尋姓名、電話前四碼、物品或備註" value={search} onChange={e=>setSearch(e.target.value)} onClear={()=>setSearch('')}/></div><span className="hint">{state.syncing?'正在建立既有空倉索引…':`共 ${list.length} 筆`} · 需求金額以月租比對</span></div>
  <p className="waiting-reminder-legend"><span><i className="dot waiting-dot-yellow"/>新增候補或新空倉配對</span><span><i className="dot waiting-dot-red"/>需求已到期未讀</span></p>
  {unitFilter&&<div className="alert success">僅顯示符合空倉 {unitFilter[1]} 的候補<button onClick={()=>setUnitFilter(null)}>顯示全部候補</button></div>}
  <section className="panel waiting-summary"><div className="table-wrap"><table className="waiting-list-table"><thead><tr><th>登記日期</th><th>姓名</th><th>候補據點</th><th>需求材積</th><th>需求月租</th><th>需求時間</th><th>需求到期時間</th><th>合適空倉</th><th>狀態</th></tr></thead><tbody>{list.map(r=><tr key={r.id}>
   <td data-label="登記日期">{r.date}</td><td data-label="姓名"><button className="text-button waiting-name" onClick={()=>open(r)}>{r.name}{state.notification(r)&&<i className={'dot waiting-dot-'+state.notification(r)} aria-label={state.notification(r)==='red'?'需求已到期未讀':'有新的候補或合適空倉'}/>}</button></td><td data-label="候補據點"><WaitingBranches labels={[
     ...r.branchIds.map((id:string)=>
      String(names.get(id)||'據點名稱載入中')),
     ...(r.otherBranches?['其它：'+r.otherBranches]:[])
    ]}/></td><td data-label="需求材積">{span(r.volumeMin,r.volumeMax)}</td><td data-label="需求月租">{span(r.priceMin,r.priceMax,' 元')}</td><td data-label="需求時間">{displayWaitingDate(r.needed)}</td><td data-label="需求到期時間">{displayWaitingDate(r.expires)}{state.isExpired(r)&&<span className="waiting-expired">已到期</span>}</td><td data-label="合適空倉"><button className="text-button" onClick={()=>open(r)}>{activeWaiting(r)?(state.ready?`${state.matches[r.id]?.length||0} 間`:'載入中…'):''}</button></td><td data-label="狀態">{r.deleting?"刪除尚未完成":labels[r.status]}</td>
  </tr>)}</tbody></table></div>{state.ready&&!list.length&&<p className="empty">沒有符合的候補紀錄。</p>}{!state.ready&&!state.error&&<p role="status">載入候補清單中…</p>}</section>
  {row&&!edit&&<div className="modal-backdrop"><section className="modal wide" role="dialog" aria-modal="true" aria-label="候補明細"><div className="modal-heading"><h2>{row.name}・候補明細</h2><button aria-label="關閉" onClick={()=>setSelected(null)}><X size={20}/></button></div>
   <dl className="waiting-details">{[['登記日期',row.date],['候補據點',branchText(row)],['電話前四碼',row.phone],['Email',row.email],['需求材積',span(row.volumeMin,row.volumeMax)],['需求月租',span(row.priceMin,row.priceMax,' 元')],['需求時間',displayWaitingDate(row.needed)],['需求到期時間',displayWaitingDate(row.expires)],['存放物品',row.items]].map(([k,v])=><div key={k}><dt>{k}</dt><dd>{v||''}</dd></div>)}</dl>
   {state.isExpired(row)&&<p className="waiting-expired">需求已到期，請確認是否仍需候補。</p>}
   <WaitingStatus value={row.status} busy={busy||!!row.deleting} onChange={next=>status(row,next)}/>
   <WaitingNotes rowId={row.id} legacy={row.note} disabled={!!row.deleting} onPendingChange={setHasUnaddedNote}/>
   
   <WaitingMatches key={row.id} active={activeWaiting(row)} units={state.matches[row.id]||[]} branchIds={row.branchIds} names={names}
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
     }}/>
   <div className="toolbar"><button className="secondary" disabled={busy||!!row.deleting} onClick={()=>startEdit(row)}>編輯</button><button className="text-button danger" disabled={busy} onClick={()=>remove(row)}>{row.deleting?"重試刪除":"刪除"}</button></div>
  </section></div>}
  {edit&&<div className="modal-backdrop"><section className="modal wide waiting-editor" role="dialog" aria-modal="true" aria-label={edit.id?'編輯候補':'新增候補'}><div className="modal-heading"><h2>{edit.id?'編輯候補':'新增候補'}</h2><button aria-label="關閉" disabled={busy} onClick={()=>setEdit(null)}><X size={20}/></button></div><form onSubmit={save}><fieldset disabled={busy} className="waiting-form">
   <div className="waiting-fields"><label>登記日期<input type="date" required value={edit.date} onChange={e=>update('date',e.target.value)}/></label><label>姓名<input required maxLength={80} value={edit.name} onChange={e=>update('name',e.target.value)}/></label><label>電話前四碼（選填）<input inputMode="numeric" maxLength={4} pattern="[0-9]{1,4}" autoComplete="off" value={edit.phone} onChange={e=>update('phone',e.target.value.replace(/\D/g,'').slice(0,4))}/></label><label>Email（選填）<input type="email" maxLength={254} value={edit.email} onChange={e=>update('email',e.target.value)}/></label></div>
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
   <div className="waiting-fields">{[['需求材積','volumeMin','volumeMax'],['需求月租金額（元）','priceMin','priceMax']].map(([label,lo,hi])=><fieldset className="waiting-range" key={lo}><legend>{label}（選填）</legend><div><input aria-label={label+'下限'} type="number" min="0" max="100000000" step="any" placeholder="下限" value={edit[lo]??''} onChange={e=>update(lo,e.target.value)}/><span>～</span><input aria-label={label+'上限'} type="number" min="0" max="100000000" step="any" placeholder="上限" value={edit[hi]??''} onChange={e=>update(hi,e.target.value)}/></div></fieldset>)}</div>
   <p className="hint">上下限都不填代表不限；只填一邊也可以。範圍包含上下限。</p>
   <WaitingDateFields value={edit} onChange={update}/><label>存放物品<textarea required maxLength={500} value={edit.items} onChange={e=>update('items',e.target.value)}/></label><WaitingNotes key={edit.id||'new'} rowId={edit.id} legacy={edit.note} drafts={edit.noteDrafts||[]} onChange={notes=>update('noteDrafts',notes)} onPendingChange={setHasUnaddedNote} disabled={busy}/>
  </fieldset>{error&&<p role="alert" className="alert error">{error}</p>}<button className="primary" disabled={busy||!directory.ready}>{busy?'儲存中…':'確認儲存'}</button></form></section></div>}
 </>;
}
