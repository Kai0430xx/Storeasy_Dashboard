import {effectiveMonths} from './actuals.js';
import {annualProgress} from './targets.js';
import {referralMonths} from './referral-months.js';
import {taipeiDate} from './domain.js';
type Row=Record<string,any>;
const pct=(n:any)=>n==null?'':`${Number(n).toFixed(2)}%`;
export default function AnnualGoalsTable({branches,records,data,year,global,onEdit}:{branches:Row[];records:Row;data:Row;year:string;global:boolean;onEdit?:(v:Row)=>void}){
 const today=taipeiDate();
 return <><h3>{year} 年度目標</h3><div className="table-wrap"><table className="mobile-goal-table" aria-label="年度目標比較"><thead><tr><th>據點</th><th>業績目標／已結束月份平均</th><th>剩餘月份平均需</th><th>轉介 3 筆以上月份數</th>{global&&onEdit&&<th>設定</th>}</tr></thead><tbody>{branches.map(b=>{
  const r=records[b.id]||{},g=r.targets?.find((v:Row)=>v.id===year),refs=r.referrals||[];
  const p=annualProgress(year,today,effectiveMonths(data[b.id]?.months||[],r.actuals||[]),refs,g,b);
  return <tr key={b.id}><td data-label="據點">{b.name}</td><td data-label="業績目標／已結束月份平均">{g?.performance!=null&&<>目標 {pct(g.performance)}{p.average!=null&&<>　平均 {pct(p.average)}</>}</>}</td><td data-label="剩餘月份平均需">{g?.performance!=null&&<>{p.totalMonths===0?'尚未開幕':p.required!=null?pct(p.required):p.remaining===0?'年度已結束':`待完整 KPI（缺 ${p.missing} 月）`}<small className="table-sub">{p.totalMonths>0?`計算 ${p.startMonth}～12 月，共 ${p.totalMonths} 個月`:''}</small></>}</td><td data-label="轉介達標月份數">{referralMonths(year,today,refs,b)}</td>{global&&onEdit&&<td data-label="設定"><button className="text-button" onClick={()=>onEdit({kind:'goal',branch:b,period:year,values:g||{}})}>設定年目標</button></td>}</tr>;
 })}</tbody></table></div></>;
}
