import {otherKeys,otherProgress} from './other-goals.js';
type Row=Record<string,any>;
export function OtherGoalEditor({value={},onChange,disabled=false,label='其它目標'}:{value?:Row;onChange:(v:Row)=>void;disabled?:boolean;label?:string}){
 const items=Object.entries(value);
 return <div className="other-goals-editor"><p>{label}（選填，可新增多項）</p>{items.map(([key,g],i)=><div key={g.id} className="other-goal-row"><label>第 {i+1} 項名稱<input disabled={disabled} aria-label={`${label} 第 ${i+1} 項名稱`} required maxLength={80} value={g.name} onChange={e=>onChange({...value,[key]:{...g,name:e.target.value}})}/></label><label>目標數量<input disabled={disabled} aria-label={`${label} 第 ${i+1} 項目標數量`} required type="number" min="0" max="1000000000" step="any" value={g.target} onChange={e=>onChange({...value,[key]:{...g,target:e.target.value}})}/></label><button type="button" disabled={disabled} onClick={()=>onChange(Object.fromEntries(items.filter(([k])=>k!==key)))}>移除第 {i+1} 項</button></div>)}<button type="button" disabled={disabled||items.length>=10} onClick={()=>{const key=otherKeys.find((k:string)=>!(k in value));if(key)onChange({...value,[key]:{id:crypto.randomUUID(),name:'',target:''}});}}>新增其它目標</button>{items.length>=10&&<small>每間據點每月最多 10 項</small>}</div>;
}
export function OtherGoalResults({goals={},actuals={},future=false}:{goals?:Row;actuals?:Row;future?:boolean}){
 const rows=otherProgress(goals,actuals,future);
 return rows.length?<div>{rows.map((r:Row)=><p key={r.id}><strong>{r.name}</strong>：目標 {r.target}／實際 {r.actual??'未填'}・{r.result==='達標'?<strong className="goal-achieved">達標</strong>:r.result}</p>)}</div>:<>—</>;
}

// storeasy-achieved-red-v1
