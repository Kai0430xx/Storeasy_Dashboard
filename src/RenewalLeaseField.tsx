import {useState} from 'react';
import {renewalStart,renewalPeriod} from './renewal-presets.js';
import './renewal-presets.css';
type Row=Record<string,any>;
export default function RenewalLeaseField({unit,value,onChange,disabled=false,label='新的租期',ariaLabel=label,hint=''}:{unit:Row;value?:string;onChange?:(value:string)=>void;disabled?:boolean;label?:string;ariaLabel?:string;hint?:string}){
 const [manual,setManual]=useState(''),[start,setStart]=useState(()=>renewalStart(unit)),[months,setMonths]=useState<number|null>(null);
 const current=value===undefined?manual:value;
 const change=(next:string)=>onChange?onChange(next):setManual(next);
 let preview='',error='';
 if(months){try{preview=renewalPeriod(start,months);}catch(e){error=e instanceof Error?e.message:String(e);}}
 return <div className="renewal-lease-field">
  <fieldset className="renewal-presets" disabled={disabled}><legend>快速選擇租期</legend>
   <label>續約開始日<input aria-label={`${ariaLabel} 開始日`} type="date" value={start} onChange={e=>setStart(e.target.value)}/></label>
   <label>續約月數<select aria-label={`${ariaLabel} 月數`} value={months??''} onChange={e=>setMonths(e.target.value?Number(e.target.value):null)}><option value="">請選擇月數</option>{Array.from({length:12},(_,i)=>i+1).map(n=><option key={n} value={n}>{n}個月</option>)}</select></label>
   {months&&<div className="renewal-preview">{error?<p role="alert">{error}</p>:<><span>租期預覽</span><strong>{preview}</strong><button className="secondary" type="button" disabled={!preview||preview===current} onClick={()=>change(preview)}>{preview===current?'已套用':'確定套用'}</button></>}</div>}
   <small>預設接續原租期隔天；可修改開始日。預覽確認後才帶入下方。</small>
  </fieldset>
  <label>{label}<input aria-label={ariaLabel} name="leasePeriod" required disabled={disabled} value={current} onChange={e=>change(e.target.value)} placeholder="2026/10/08－2027/04/07" autoComplete="off"/><small>特殊租期或非整月，可直接手動輸入完整起訖日期。</small>{hint&&<small>{hint}</small>}</label>
 </div>;
}
