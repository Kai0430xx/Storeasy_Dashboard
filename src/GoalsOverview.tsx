import GoalDisclosure from "./GoalDisclosure";
import AnnualGoalsTable from './AnnualGoalsTable';
import MonthlyGoalsTable from './MonthlyGoalsTable';
import YearGoalsView from './YearGoalsView';
import {OtherGoalEditor,OtherGoalResults} from './OtherGoals';
import MonthlyEntry from "./MonthlyEntry";
import { effectiveMonths } from "./actuals.js";
import { compareBranches } from "./branch-order.js";
import {useEffect,useState} from 'react';
import { collection, getDocs, onSnapshot, doc, documentId, getDoc, query, where } from "firebase/firestore";
import {db} from './firebase';
import {saveGoal} from './targets-api';
import {annualProgress} from './targets.js';
import {taipeiDate} from './domain.js';
type Row=Record<string,any>;
const pct=(n:any)=>n==null?'—':`${Number(n).toFixed(2)}%`;
const mark=(v:any,g:any)=>g==null?'—':v==null?'待資料':v>=g?<strong className="goal-achieved">達標</strong>:'未達標';
const keys=['occupancy','performance','referrals'];
export default function GoalsOverview({branches,records:supplied,data,month,global,onEdit,collapsible=false}:{branches:Row[];records?:Row;data:Row;month:string;global:boolean;onEdit?:(v:Row)=>void;collapsible?:boolean}){
 const [live,setLive]=useState<Row>({}),[all,setAll]=useState<Row[]|null>(null),[draft,setDraft]=useState<Row>({}),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[period,setPeriod]=useState(month);
 const year=month.slice(0,4),today=taipeiDate(),records=supplied||live;
 useEffect(()=>{if(supplied)return;setLive({});const stops=branches.flatMap(b=>['targets','referrals','actuals'].map(c=>onSnapshot(query(collection(db,'branches',b.id,c),where(documentId(),'>=',year),where(documentId(),'<',String(Number(year)+1))),s=>setLive(prev=>({...prev,[b.id]:{...prev[b.id],[c]:s.docs.map(d=>({id:d.id,...d.data()}))}})),e=>setMessage(e.message))));return()=>stops.forEach(s=>s());},[Boolean(supplied),branches.map(b=>b.id).join(','),year]);
 useEffect(()=>{if(!busy){setAll(null);setMessage('');}},[month]);
 const monthsFor=(b:Row)=>effectiveMonths(data[b.id]?.months||[],records[b.id]?.actuals||[]);
 const goal=(b:Row,p:string)=>records[b.id]?.targets?.find((v:Row)=>v.id===p);
 const referrals=(b:Row)=>records[b.id]?.referrals||[];
 const has=(p:string,k:string)=>branches.some(b=>goal(b,p)?.[k]!=null);
 const monthlyRef=(b:Row)=>referrals(b).find((r:Row)=>r.id===month);
 const mo=has(month,'occupancy'),mp=has(month,'performance'),mr=has(month,'referrals')||branches.some(b=>monthlyRef(b)?.count>0);
 const mx=branches.some(b=>Object.keys(goal(b,month)?.other||{}).length>0);
 const ao=has(year,'occupancy'),ap=has(year,'performance'),ar=has(year,'referrals')||branches.some(b=>referrals(b).some((r:Row)=>r.month?.startsWith(year+'-')&&r.month<=today.slice(0,7)&&r.count>0));
 async function loadDraft(list:Row[],p:string){const rows=await Promise.all(list.map(async b=>{const s=await getDoc(doc(db,'branches',b.id,'targets',p));const g=s.data();return [b.id,{...Object.fromEntries(keys.map(k=>[k,g?.[k]??''])),other:g?.other||{}}] as const;}));setDraft(Object.fromEntries(rows));}
 async function open(){setBusy(true);setMessage('');try{const s=await getDocs(collection(db,'branches'));const list=s.docs.map(d=>({id:d.id,...d.data()})).filter((b:Row)=>!b.archived).sort(compareBranches);if(!list.length)throw Error('尚無據點');await loadDraft(list,month);setPeriod(month);setAll(list);}catch(e){setMessage(e instanceof Error?e.message:String(e));}finally{setBusy(false);}}
 async function changePeriod(p:string){if(!all)return;setBusy(true);setMessage('');try{await loadDraft(all,p);setPeriod(p);}catch(e){setMessage(String(e));}finally{setBusy(false);}}
 async function apply(e:React.FormEvent<HTMLFormElement>){e.preventDefault();if(!all)return;setBusy(true);let completed=0;const failed:string[]=[];for(const b of all){try{await saveGoal(b.id,period,draft[b.id]);completed++;}catch(err){failed.push(`${b.name}：${err instanceof Error?err.message:String(err)}`);}setMessage(`已處理 ${completed+failed.length}/${all.length} 間`);}setBusy(false);setMessage(`成功 ${completed} 間${failed.length?`；失敗 ${failed.length} 間：${failed.join('；')}`:''}`);if(!failed.length)setAll(null);}
 return <section className="panel target-panel">
  <div className="panel-heading"><h2>目標與轉介概況</h2><button disabled={busy} onClick={async()=>{
      setBusy(true);
      setMessage("");
      try {
        const {exportAnnualTargets}=await import("./annual-export");
        await exportAnnualTargets(year);
        setMessage(`${year} 年度 Excel 已匯出`);
      } catch(e) {
        setMessage(e instanceof Error?e.message:String(e));
      } finally {
        setBusy(false);
      }
    }}>匯出 {year} 年度目標與轉介 Excel</button><YearGoalsView branches={branches} records={records} data={data} year={year}/>{global&&<button className="primary" disabled={busy} onClick={open}>逐店設定全部據點目標</button>}</div>
  <p>依上方據點篩選顯示；未設定的指標隱藏，已填寫的額外轉介仍會顯示。</p>{message&&<p role="status">{message}</p>}
  <GoalDisclosure key={"MonthlyGoalsTable-"+month} collapsed={collapsible} title={month+" 每月目標"}><MonthlyGoalsTable branches={branches} records={records} data={data} month={month} global={global} onEdit={onEdit}/></GoalDisclosure>
  <GoalDisclosure key={"AnnualGoalsTable-"+year} collapsed={collapsible} title={year+" 年度目標"}><AnnualGoalsTable branches={branches} records={records} data={data} year={year} global={global} onEdit={onEdit}/></GoalDisclosure>
  {all&&<div className="modal-backdrop"><section className="modal wide" role="dialog" aria-modal="true" aria-label="逐店設定全部據點目標"><div className="modal-heading"><h2>逐店設定全部據點目標</h2><button aria-label="關閉" disabled={busy} onClick={()=>setAll(null)}>×</button></div><p>每間據點輸入自己的目標。已載入原設定；清空欄位代表取消該店這項目標。</p><form onSubmit={apply}><label>目標期間<select aria-label="目標期間" disabled={busy} value={period} onChange={e=>changePeriod(e.target.value)}><option value={month}>{month} 每月目標</option><option value={year}>{year} 年度目標</option></select></label><fieldset disabled={busy}><div className="table-wrap"><table><thead><tr><th>據點</th><th>出租率（%）</th><th>業績完成率（%）</th>{period.length===7&&<th>轉介數量</th>}{period.length===7&&<th>其它目標</th>}</tr></thead><tbody>{all.map(b=><tr key={b.id}><td>{b.name}</td>{keys.filter(k=>period.length===7||k!=='referrals').map(k=><td key={k}><input aria-label={`${b.name} ${k==='occupancy'?'出租率':k==='performance'?'業績完成率':'轉介數量'}`} type="number" min="0" max={k==='occupancy'?100:undefined} step={k==='referrals'?'1':'0.01'} value={draft[b.id]?.[k]??''} onChange={e=>setDraft(v=>({...v,[b.id]:{...v[b.id],[k]:e.target.value}}))}/></td>)}{period.length===7&&<td><OtherGoalEditor label={`${b.name} 其它目標`} value={draft[b.id]?.other||{}} disabled={busy} onChange={other=>setDraft(v=>({...v,[b.id]:{...v[b.id],other}}))}/></td>}</tr>)}</tbody></table></div></fieldset>{message&&<p role="status">{message}</p>}<button className="primary" disabled={busy}>儲存全部據點各自的目標</button></form></section></div>}
 </section>;
}

// storeasy-other-monthly-v1

// storeasy-achieved-red-v1

// storeasy-year-goals-view-v1

// storeasy-opening-month-v1

// storeasy-monthly-goals-clean-v1

// storeasy-annual-renew-backfill-v2
