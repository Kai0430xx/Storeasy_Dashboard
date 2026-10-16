import {displayWaitingDate,waitingStatuses,waitingStatusLabels} from './waiting-domain.js';
type Row=Record<string,any>;
const labels:Record<string,string>=waitingStatusLabels;
export function WaitingDateFields({value,onChange}:{value:Row;onChange:(key:string,value:string)=>void}){
 return <div className="waiting-fields waiting-date-fields">
  <label>需求時間（選填）<input inputMode="numeric" placeholder="YYYY/MM/DD" maxLength={10} value={displayWaitingDate(value.needed)} onChange={e=>onChange('needed',e.target.value)}/>{/^\d{2}\/\d{2}$/.test(value.needed||'')&&<small className="hint">舊資料缺少年份，請補完整日期；尚未確認可先保留。</small>}</label>
  <label>需求到期時間（選填）<input inputMode="numeric" placeholder="YYYY/MM/DD" maxLength={10} value={displayWaitingDate(value.expires)} onChange={e=>onChange('expires',e.target.value)}/></label>
 </div>;
}
export function WaitingStatus({value,busy,onChange}:{value:string;busy:boolean;onChange:(status:string)=>void}){
 return <fieldset className="waiting-detail-status"><legend>候補狀態（單選）</legend><div className="waiting-status-tabs">{waitingStatuses.map(s=><label key={s}><input type="checkbox" checked={value===s} disabled={busy} onChange={e=>onChange(e.target.checked?s:'waiting')}/>{labels[s]}</label>)}</div></fieldset>;
}
