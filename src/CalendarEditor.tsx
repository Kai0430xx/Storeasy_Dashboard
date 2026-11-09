import {useEffect,useRef,useState,ReactNode} from 'react';
import {createPortal} from 'react-dom';
import {auth} from './firebase';
import {CalRow,calError,useCalendarCategories,useCalendarDirectory} from './calendar-client';
import './calendar.css';
export function CalendarModal({title,onClose,children,busy=false}:{title:string;onClose:()=>void;children:ReactNode;busy?:boolean}){
 const ref=useRef<HTMLElement>(null),close=useRef(onClose);close.current=onClose;
 useEffect(()=>{const old=document.activeElement as HTMLElement,overflow=document.body.style.overflow;document.body.style.overflow='hidden';ref.current?.querySelector<HTMLElement>('input,button,select')?.focus();return()=>{document.body.style.overflow=overflow;old?.focus?.();};},[]);
 return createPortal(<div className="modal-backdrop calendar-backdrop" onKeyDown={e=>{e.stopPropagation();if(e.key==='Escape'&&!busy)close.current();if(e.key==='Tab'){const els=Array.from(ref.current?.querySelectorAll<HTMLElement>('button,input,select,textarea,[tabindex="0"]')||[]).filter(el=>!el.hasAttribute('disabled'));if(e.shiftKey&&document.activeElement===els[0]){e.preventDefault();els.at(-1)?.focus();}else if(!e.shiftKey&&document.activeElement===els.at(-1)){e.preventDefault();els[0]?.focus();}}}}><section className="modal wide calendar-modal" role="dialog" aria-modal="true" aria-label={title} ref={ref}><div className="modal-heading"><h2>{title}</h2><button aria-label="關閉" disabled={busy} onClick={onClose}>×</button></div>{children}</section></div>,document.body);
}
function CalendarTime({label,value,onChange,optional=false}:{label:string;value:string;onChange:(value:string)=>void;optional?:boolean}){
 const [hour='',minute='']=String(value||'').split(':');
 return <fieldset className="calendar-time"><legend>{label}{optional?'（選填）':''}</legend><div><select required={!optional} aria-label={label+'（時）'} value={hour} onChange={e=>onChange(e.target.value?e.target.value+':'+(minute||'00'):'')}>{optional&&<option value="">未設定</option>}{Array.from({length:24},(_,i)=>String(i).padStart(2,'0')).map(v=><option key={v} value={v}>{v} 時</option>)}</select><span aria-hidden="true">:</span><select required={!optional} aria-label={label+'（分）'} value={minute} onChange={e=>onChange(e.target.value?(hour||'09')+':'+e.target.value:'')}>{optional&&<option value="">未設定</option>}{Array.from({length:60},(_,i)=>String(i).padStart(2,'0')).map(v=><option key={v} value={v}>{v} 分</option>)}</select></div></fieldset>;
}
export default function CalendarEditor({initial,ownerId,title,onClose,onSave,busy=false,taskLinked=false}:{initial:CalRow;ownerId:string;title:string;onClose:()=>void;onSave:(value:CalRow)=>Promise<void>|void;busy?:boolean;taskLinked?:boolean}){
 const [value,setValue]=useState<CalRow>({...initial,endDate:initial.endDateUnset?'':initial.endDate,viewerIds:[...(initial.viewerIds||[])]});const [shared,setShared]=useState(!!initial.viewerIds?.length),[error,setError]=useState('');
 const {people,error:directoryError}=useCalendarDirectory(),categories=useCalendarCategories(ownerId,initial.id);const operation=useRef('op_'+crypto.randomUUID());
 const field=(key:string,newValue:any)=>setValue(v=>({...v,[key]:newValue,...(key==='endDate'?{endDateUnset:!newValue}:{})}));
 return <CalendarModal title={title} onClose={onClose} busy={busy}><form onSubmit={async e=>{e.preventDefault();e.stopPropagation();setError('');try{await onSave({...value,viewerIds:shared?value.viewerIds:[],operationId:operation.current});}catch(e){setError(calError(e));}}}>
  <label>標題<input required maxLength={120} value={value.title} onChange={e=>field('title',e.target.value)}/></label>
  <label className="calendar-check"><input type="checkbox" checked={value.allDay} onChange={e=>field('allDay',e.target.checked)}/>全天</label>
  <div className="calendar-editor-grid"><label>開始日期<input type="date" required min="2000-01-01" max="2099-12-31" value={value.startDate} onChange={e=>{const date=e.target.value;setValue(v=>({...v,startDate:date,endDate:v.endDate&&v.endDate<date?date:v.endDate}));}}/></label><label>結束日期（選填）<input aria-label="結束日期" type="date" min={value.startDate} max="2099-12-31" value={value.endDate} onChange={e=>field('endDate',e.target.value)}/></label>
  {!value.allDay&&<><CalendarTime label="開始時間" value={value.startTime} onChange={v=>field('startTime',v)}/><CalendarTime optional label="結束時間" value={value.endTime} onChange={v=>field('endTime',v)}/></>}</div>
  <label>分類<select aria-label="分類" value={value.categoryId} onChange={e=>field('categoryId',e.target.value)}><option value="">未分類</option>{categories.rows.filter(r=>!r.archived||r.id===value.categoryId).map(r=><option key={r.id} value={r.id}>{r.name}{r.archived?'（已停用）':''}</option>)}</select></label>
  <label>備註<textarea rows={4} maxLength={5000} value={value.notes} onChange={e=>field('notes',e.target.value)}/></label>
  <fieldset className="calendar-sharing"><legend>可查看對象</legend><label className="calendar-check"><input type="radio" name="calendar-sharing" checked={!shared} onChange={()=>setShared(false)}/>私人</label><label className="calendar-check"><input type="radio" name="calendar-sharing" checked={shared} onChange={()=>setShared(true)}/>分享給選定人員</label>
  {shared&&<div className="calendar-people">{people.filter(p=>p.id!==ownerId).map(p=><label className="calendar-check" key={p.id}><input type="checkbox" checked={value.viewerIds.includes(p.id)} onChange={e=>field('viewerIds',e.target.checked?[...value.viewerIds,p.id]:value.viewerIds.filter((id:string)=>id!==p.id))}/>{p.name}</label>)}{!people.length&&<p>人員名單載入中…</p>}</div>}</fieldset>
  {taskLinked&&<p className="hint">標題或日期如需同步原待辦，儲存時會再詢問。時間、分類、分享與備註不會覆蓋待辦討論。</p>}
  {(error||directoryError||categories.error)&&<p role="alert" className="alert error">{error||directoryError||categories.error}</p>}
  <button className="primary" disabled={busy||!!directoryError}>{busy?'處理中…':title.includes('申請')?'送出修改申請':'儲存'}</button>
 </form></CalendarModal>;
}
export function WorkCalendarOption({form,onChange}:{form:CalRow;onChange:(value:CalRow)=>void}){
 const [open,setOpen]=useState(false);const uid=auth.currentUser?.uid||'';
 return <div className="work-calendar-option"><label className="calendar-check"><input type="checkbox" checked={!!form.calendarDraft||open} onChange={e=>{if(e.target.checked)setOpen(true);else onChange({...form,calendarDraft:null});}}/>加入日曆</label>{form.calendarDraft&&<><span>{form.calendarDraft.startDate} {form.calendarDraft.allDay?'全天':form.calendarDraft.startTime} · {form.calendarDraft.viewerIds.length?'已分享':'私人'}</span><button className="text-button" type="button" onClick={()=>setOpen(true)}>修改日曆資料</button></>}{open&&<CalendarEditor title="待辦加入日曆" ownerId={uid} initial={form.calendarDraft||{title:form.title||'',startDate:form.due||new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Taipei'}),endDate:'',endDateUnset:true,startTime:'09:00',endTime:'',allDay:false,categoryId:'',notes:form.description||'',viewerIds:[]}} onClose={()=>setOpen(false)} onSave={value=>{onChange({...form,calendarDraft:value});setOpen(false);}}/>}</div>;
}
