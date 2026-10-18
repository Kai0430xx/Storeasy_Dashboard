import {annualExportRows} from './annual-export';
import MonthlyEntry from './MonthlyEntry';
import {taipeiDate} from './domain.js';
type Row=Record<string,any>;
const pct=(n:number)=>`${Number(n).toFixed(2)}%`;
function values(target:any,actual:any,format:(n:any)=>any=(n)=>n,red=false){
 return <>{target!=null&&<span>目標 {format(target)}</span>}{actual!=null&&<span className={red?"goal-achieved":undefined}>{target!=null?'　':''}實際 {format(actual)}</span>}</>;
}
export default function MonthlyGoalsTable({branches,records,data,month,global,onEdit}:{branches:Row[];records:Row;data:Row;month:string;global:boolean;onEdit?:(v:Row)=>void}){
 const combined=Object.fromEntries(branches.map(b=>[b.id,{...records[b.id],months:data[b.id]?.months||[]}])) as Row;
 const rows=annualExportRows(branches,combined,month.slice(0,4),taipeiDate()).filter(r=>r.month===month);
 const goal=(id:string)=>records[id]?.targets?.find((g:Row)=>g.id===month);
 const mo=rows.some(r=>r.occupancyTarget!=null),mp=rows.some(r=>r.performanceTarget!=null),mr=rows.some(r=>r.referralTarget!=null||r.referrals>0),mx=rows.some(r=>r.other.length>0);
 return <><h3>{month} 每月目標</h3>{!mo&&!mp&&!mr&&!mx&&<p>本月尚無目標或轉介紀錄</p>}<div className="table-wrap"><table className="mobile-goal-table" aria-label="每月目標比較"><thead><tr><th>據點</th>{mo&&<th>出租率目標／實際</th>}{mp&&<th>業績完成率目標／實際</th>}{mx&&<th>其它目標／實際</th>}{mr&&<th>轉介目標／實際</th>}<th>設定</th><th>是否達標</th></tr></thead><tbody>{branches.map(b=>{
  const r=rows.find(v=>v.branchId===b.id)!;const g=goal(b.id);
  const hasGoal=r.occupancyTarget!=null||r.performanceTarget!=null||r.referralTarget!=null||r.other.length>0;
  const corrected=records[b.id]?.actuals?.find((a:Row)=>a.id===month);
  return <tr key={b.id}><td data-label="據點">{b.name}{(corrected?.occupancy!=null||corrected?.performance!=null)&&<small className="table-sub">含手動修正</small>}</td>
   {mo&&<td data-label="出租率目標／實際">{r.occupancyTarget!=null&&values(r.occupancyTarget,r.occupancy,pct)}</td>}
   {mp&&<td data-label="業績完成率目標／實際">{r.performanceTarget!=null&&values(r.performanceTarget,r.performance,pct)}</td>}
   {mx&&<td data-label="其它目標／實際">{r.other.map((o:Row)=><p key={o.id}>{o.name}：{values(o.target,o.actual)}</p>)}</td>}
   {mr&&<td data-label="轉介目標／實際">{(r.referralTarget!=null||r.referrals>0)&&values(r.referralTarget,r.referrals,(n)=>n,r.referrals>=3)}</td>}
   <td data-label="設定">{global&&onEdit&&<button className="text-button" onClick={()=>onEdit({kind:'goal',branch:b,period:month,values:g||{}})}>設定月目標</button>}<MonthlyEntry branch={b} month={month}/></td>
   <td data-label="是否達標">{hasGoal&&(r.overall==='達標'?<strong className="goal-achieved">達標</strong>:r.overall)}</td>
  </tr>;
 })}</tbody></table></div></>;
}

// storeasy-referral-red-v1
