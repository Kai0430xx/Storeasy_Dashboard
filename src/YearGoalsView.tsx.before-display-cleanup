import {useEffect,useRef,useState} from 'react';
import {annualExportRows} from './annual-export';
import {taipeiDate} from './domain.js';
type Row=Record<string,any>;
const percent=(n:any)=>n==null?'未填':`${Number(n).toFixed(2)}%`;
export default function YearGoalsView({branches,records,data,year}:{branches:Row[];records:Row;data:Row;year:string}){
 const [open,setOpen]=useState(false),[selected,setSelected]=useState('');
 const modal=useRef<HTMLElement>(null);
 useEffect(()=>{setOpen(false);setSelected('');},[year,branches.map(b=>b.id).join(',')]);
 useEffect(()=>{
  if(!open)return;
  const previous=document.activeElement as HTMLElement|null;
  modal.current?.querySelector<HTMLButtonElement>('button')?.focus();
  const key=(e:KeyboardEvent)=>{
   if(e.key==='Escape'){e.preventDefault();setOpen(false);}
   if(e.key==='Tab'){
    const nodes=Array.from(modal.current?.querySelectorAll<HTMLElement>('button:not(:disabled),select:not(:disabled),[tabindex="0"]')||[]);
    const first=nodes[0],last=nodes.at(-1);
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}
    else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}
   }
  };
  document.addEventListener('keydown',key);
  return()=>{document.removeEventListener('keydown',key);if(previous?.isConnected)previous.focus();};
 },[open]);
 const branch=branches.find(b=>b.id===selected),record=branch?records[branch.id]:null;
 const ready=branch&&['targets','referrals','actuals'].every(k=>Array.isArray(record?.[k]))&&Array.isArray(data[branch.id]?.months);
 const rows=ready?annualExportRows([branch],{[branch.id]:{...record,months:data[branch.id].months}},year,taipeiDate()):[];
 function items(r:Row){
  if(r.notOpen)return [{name:'尚未開幕，不納入年度計算',actual:'—',result:'未開幕'}];
  const list:Row[]=[];
  if(r.occupancyTarget!=null)list.push({name:`出租率：${percent(r.occupancyTarget)}`,actual:percent(r.occupancy),result:r.occupancyResult});
  if(r.performanceTarget!=null)list.push({name:`業績完成率：${percent(r.performanceTarget)}`,actual:percent(r.performance),result:r.performanceResult});
  if(r.referralTarget!=null)list.push({name:`轉介數量：${r.referralTarget}`,actual:r.referrals??'未填',result:r.referralResult});
  for(const g of r.other||[])list.push({name:`${g.name}：${g.target}`,actual:g.actual??'未填',result:g.result});
  return list.length?list:[{name:'本月未設定目標',actual:'—',result:'未設定'}];
 }
 const status=(text:string)=>text==='達標'?<strong className="goal-achieved">達標</strong>:text;
 return <>
  <button disabled={!branches.length} onClick={()=>{setSelected(branches.length===1?branches[0].id:'');setOpen(true);}}>查看該據點當年度目標一覽</button>
  {open&&<div className="modal-backdrop" onClick={e=>{if(e.target===e.currentTarget)setOpen(false);}}><section ref={modal} className="modal year-goals-modal" role="dialog" aria-modal="true" aria-label="據點當年度目標一覽">
   <div className="panel-heading"><h2>{branch?.name||'據點'}・{year} 年度目標一覽</h2><button aria-label="關閉年度目標一覽" onClick={()=>setOpen(false)}>×</button></div>
   {branches.length>1&&<label>選擇據點<select aria-label="年度目標一覽據點" value={selected} onChange={e=>setSelected(e.target.value)}><option value="">請選擇據點</option>{branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label>}
   <p>依 1～12 月列出各月設定的目標；數值採 KPI 或已儲存的手動修正。「其它」採手填成果。當月所有設定的目標都達成才算達標，以紅字顯示；缺少實際數值顯示資料未齊。轉介超過 3 筆以紅字標示。</p>
   {!branch?<p>請選擇要查看的據點。</p>:!ready?<p role="status">載入年度資料中…</p>:<div className="table-wrap year-goals-table" tabIndex={0} aria-label="年度目標表格捲動區"><table aria-label="據點全年每月目標"><thead><tr><th>月份</th><th>目標內容</th><th>實際數值</th><th>是否達標</th><th>轉介數量</th></tr></thead><tbody>{rows.flatMap(r=>{const list=items(r);return list.map((item,i)=><tr key={`${r.month}-${i}`}>
    {i===0&&<th scope="rowgroup" rowSpan={list.length}>{year}年{Number(r.month.slice(5))}月</th>}<td>{item.name}</td><td>{item.actual}</td>{i===0&&<><td rowSpan={list.length}>{status(r.overall)}</td><td rowSpan={list.length}>{r.referrals==null?'未填':r.referrals>=3?<strong className="goal-achieved">{r.referrals} 筆</strong>:`${r.referrals} 筆`}</td></>}
   </tr>);})}</tbody></table></div>}
  </section></div>}
 </>;
}

// storeasy-month-result-v1

// storeasy-opening-month-v1

// storeasy-referral-red-v1
