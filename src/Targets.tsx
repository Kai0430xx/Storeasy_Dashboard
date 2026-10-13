import {OtherGoalEditor,OtherGoalResults} from './OtherGoals';
import { effectiveMonths } from "./actuals.js";
import GoalsOverview from "./GoalsOverview";
import {useEffect,useState} from 'react';
import { collection, onSnapshot, documentId, getDocs, query, where } from "firebase/firestore";
import {db} from './firebase';
import {taipeiDate} from './domain.js';
import {annualProgress,exitCategories,vacantDays} from './targets.js';
import {saveGoal,saveReferrals,saveVacantSince} from './targets-api';
type Row=Record<string,any>;
const percent=(n:any)=>n==null?'待匯入':`${Number(n).toFixed(2)}%`;
const result=(actual:any,target:any)=>target==null?'未設定':actual==null?'待匯入':actual>=target?<strong className="goal-achieved">已達標</strong>:'未達標';
export default function Targets({branches,month,profile,data}:{branches:Row[];month:string;profile:Row;data:Row}){
 const [records,setRecords]=useState<Row>({}),[editing,setEditing]=useState<Row|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [entries,setEntries]=useState<Row[]>([]),[history,setHistory]=useState<Row|null>(null);
 useEffect(()=>{setEditing(null);setHistory(null);setError('');setNotice('');},[month]);
 const today=taipeiDate(),year=month.slice(0,4),global=['admin','supervisor'].includes(profile.role),edit=global||profile.role==='manager';
 useEffect(()=>{setRecords({});const stops=branches.flatMap(b=>['targets','referrals','actuals'].map(c=>onSnapshot(query(collection(db,'branches',b.id,c),where(documentId(),'>=',year),where(documentId(),'<',String(Number(year)+1))),s=>setRecords(prev=>({...prev,[b.id]:{...prev[b.id],[c]:s.docs.map(d=>({id:d.id,...d.data()}))}})),e=>setError(e.message))));return()=>stops.forEach(s=>s());},[branches.map(b=>b.id).join(','),year]);
 async function run(fn:()=>Promise<unknown>){setBusy(true);setError('');try{await fn();setEditing(null);setNotice('已儲存');}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}}
 return <>
  <header className="page-header"><div><p>依上方選取月份查看月度目標及該年度進度。目標修改會保留紀錄。</p></div></header>
  {error&&<div role="alert" className="alert error">{error}</div>}{notice&&<div role="status" className="alert success">{notice}</div>}
  {!branches.length&&<p>尚無可查看據點</p>}
  <GoalsOverview
    branches={branches}
    records={records}
    data={data}
    month={month}
    global={global}
    onEdit={setEditing}
  />
  <details>
    <summary>各據點詳細資料與轉介填寫（點此展開）</summary>
  {branches.map(b=>{
   const r=records[b.id]||{},goals=r.targets||[],refs=r.referrals||[];
   const monthly=goals.find((g:Row)=>g.id===month),annual=goals.find((g:Row)=>g.id===year),ref=refs.find((v:Row)=>v.id===month);
   const months=effectiveMonths(data[b.id]?.months||[],r.actuals||[]),kpi=months.find((m:Row)=>(m.id||m.month)===month&&m.source==='import'),metrics=kpi?.kpiMetrics||{};
   const occupancy=metrics.occupancy??(kpi?.total>0?kpi.rented/kpi.total*100:null);
   const progress=annualProgress(year,today,months,refs,annual,b);
   return <section className="panel target-panel" key={b.id}>
    <div className="panel-heading"><h2>{b.name}</h2><button className="text-button" onClick={async()=>{
          try {
            const s=await getDocs(collection(db,'branches',b.id,'targetHistory'));
            setHistory({
              branch:b,
              items:s.docs.map(d=>({id:d.id,...d.data()}))
            });
          } catch(e) {
            setError(e instanceof Error?e.message:String(e));
          }
        }}>目標修改紀錄</button></div>
    <h3>{month} 每月目標</h3>{kpi?.manualActuals&&<p>此月包含手動修正值；原 KPI 保留，可在上方「設定實際數值」查看及恢復。</p>}
    {global&&<button onClick={()=>setEditing({kind:'goal',branch:b,period:month,values:monthly||{}})}>設定每月目標</button>}
    <div className="table-wrap"><table><thead><tr><th>指標</th><th>目標</th><th>實際</th><th>結果</th></tr></thead><tbody>
     {(monthly?.occupancy!=null)&&<tr><td>出租率</td><td>{monthly?.occupancy==null?'未設定':percent(monthly.occupancy)}</td><td>{percent(occupancy)}</td><td>{result(occupancy,monthly?.occupancy)}</td></tr>}
     {(monthly?.performance!=null)&&<tr><td>業績完成率</td><td>{monthly?.performance==null?'未設定':percent(monthly.performance)}</td><td>{percent(metrics.performance)}</td><td>{result(metrics.performance,monthly?.performance)}</td></tr>}
     {(monthly?.referrals!=null||ref?.count>0)&&<tr><td>轉介數量</td><td>{monthly?.referrals??'未設定'}</td><td>{ref?.count??'未填寫'} {ref?.count>3&&<span className="referral-bonus">超過 3 筆・年終加成</span>}</td><td>{result(ref?.count,monthly?.referrals)}{monthly?.referrals!=null&&!ref&&'・必填'}</td></tr>}
     {Object.keys(monthly?.other||{}).length>0&&<tr><td>其它</td><td colSpan={3}><OtherGoalResults goals={monthly.other} actuals={r.actuals?.find((a:Row)=>a.id===month)?.other} future={month>today.slice(0,7)}/></td></tr>}
    </tbody></table></div>
    <p className="hint">KPI 來源：{kpi?.sourceFile||'待匯入'}。{metrics.revenue!=null&&`當年當月業績：NT$ ${Number(metrics.revenue).toLocaleString()}`} 舊 KPI 若未含完成率，請重新匯入原檔。</p>
    <h3>{year} 年度目標</h3>
    {global&&<button onClick={()=>setEditing({kind:'goal',branch:b,period:year,values:annual||{}})}>設定年度目標</button>}
    <p>{progress.totalMonths>0?`年度計算 ${progress.startMonth}～12 月，共 ${progress.totalMonths} 個月。`:'此年度尚未開幕。'}已結束 {progress.completed} 個月，剩餘 {progress.remaining} 個月。{progress.missing>0&&`有 ${progress.missing} 個已結束月份缺少業績完成率 KPI，補齊前不推算年度需求。`}</p>
    <div className="table-wrap"><table><thead><tr><th>指標</th><th>年度目標</th><th>目前進度</th><th>尚需完成</th></tr></thead><tbody>
     {(annual?.performance!=null)&&<tr><td>業績完成率（全年平均）</td><td>{annual?.performance==null?'未設定':percent(annual.performance)}</td><td>{progress.average==null?'待完整 KPI':percent(progress.average)}{progress.totalMonths>0&&progress.completed===progress.totalMonths&&<>・{result(progress.average,annual?.performance)}</>}</td><td>{annual?.performance==null?'未設定':progress.remaining===0?'年度已結束':progress.required==null?'待完整 KPI':`剩餘月份平均需 ${percent(progress.required)}`}</td></tr>}
     {(annual?.occupancy!=null)&&<tr><td>出租率（12 月達標）</td><td>{annual?.occupancy==null?'未設定':percent(annual.occupancy)}</td><td>{percent(progress.occupancy)}{progress.finalOccupancy!=null&&<>・12 月 {result(progress.finalOccupancy,annual?.occupancy)}</>}</td><td>{annual?.occupancy==null?'未設定':progress.occupancy==null?'待資料':`差 ${Math.max(0,annual.occupancy-progress.occupancy).toFixed(2)} 個百分點${progress.unitsNeeded==null?'':`，需再出租 ${progress.unitsNeeded} 間`}`}</td></tr>}
     {(annual?.referrals!=null||progress.referred>0)&&<tr><td>轉介數量（全年加總）</td><td>{annual?.referrals??'未設定'}</td><td>本年度已填合計 {progress.referred} 間</td><td>{annual?.referrals==null?'未設定':`差 ${Math.max(0,annual.referrals-progress.referred)} 間${progress.referralsRequired==null?'':`，剩餘每月平均 ${progress.referralsRequired.toFixed(2)} 間`}`}</td></tr>}
    </tbody></table></div>
    <p className="hint">年度業績採每月完成率平均。出租率以倉位數計算；本年度差距使用目前倉位現況，12 月結果使用匯入 KPI。倉位數變動時所需間數會隨之調整。</p>
    <h3>本月轉介明細 {monthly?.referrals!=null?'（必填）':'（選填）'}</h3>
    {edit&&month<=today.slice(0,7)&&<button onClick={()=>{setEntries(ref?.entries||[]);setEditing({kind:'referrals',branch:b});}}>填寫／修改轉介</button>}
    <p>數量依明細筆數計算；沒有轉介也可以明確儲存 0 筆。</p>
    <div className="table-wrap"><table><thead><tr><th>倉位編號</th><th>租期</th></tr></thead><tbody>{ref?.entries?.map((e:Row,i:number)=><tr key={i}><td>{e.code}</td><td>{e.leasePeriod}</td></tr>)}</tbody></table></div>
   </section>;
  })}
  </details>
  {editing&&<div className="modal-backdrop"><section className="modal" role="dialog" aria-modal="true" aria-label={editing.kind==='goal'?'設定目標':'填寫轉介'}><button disabled={busy} aria-label="關閉" onClick={()=>setEditing(null)}>×</button><h2>{editing.branch.name}・{editing.period||month}</h2>
   {error&&<div role="alert">{error}</div>}
   {editing.kind==='goal'?<form onSubmit={e=>{e.preventDefault();const v=Object.fromEntries(new FormData(e.currentTarget));run(()=>saveGoal(editing.branch.id,editing.period,{...v,other:editing.values.other||{}}));}}>
    <p>留白代表未設定；百分比請輸入 80，表示 80%。</p>
    <label>出租率目標（%）<input name="occupancy" type="number" min="0" max="100" step="0.01" defaultValue={editing.values.occupancy??''}/></label>
    <label>業績完成率目標（%）<input name="performance" type="number" min="0" step="0.01" defaultValue={editing.values.performance??''}/></label>
    <label>轉介數量目標<input name="referrals" type="number" min="0" step="1" defaultValue={editing.values.referrals??''}/></label>
    {editing.period.length===7&&<OtherGoalEditor value={editing.values.other||{}} disabled={busy} onChange={other=>setEditing(v=>v?{...v,values:{...v.values,other}}:v)}/>}
    <button className="primary" disabled={busy}>儲存目標</button>
   </form>:<form onSubmit={e=>{e.preventDefault();run(()=>saveReferrals(editing.branch.id,month,entries));}}>
    <p>轉介 {entries.length} 筆 {entries.length>3?'・超過 3 間，年終加成':''}</p>
    {entries.map((entry,i)=><fieldset key={i}><legend>第 {i+1} 筆</legend><label>倉位編號<input required maxLength={80} value={entry.code} onChange={e=>setEntries(v=>v.map((x,j)=>j===i?{...x,code:e.target.value}:x))}/></label><label>租期<input required placeholder="2026/10/08－2027/04/07" value={entry.leasePeriod} onChange={e=>setEntries(v=>v.map((x,j)=>j===i?{...x,leasePeriod:e.target.value}:x))}/></label><button type="button" onClick={()=>setEntries(v=>v.filter((_,j)=>j!==i))}>移除此筆</button></fieldset>)}
    <button type="button" disabled={entries.length>=200} onClick={()=>setEntries(v=>[...v,{code:'',leasePeriod:''}])}>新增轉介明細</button><button className="primary" disabled={busy}>儲存 {entries.length} 筆轉介</button>
   </form>}
  </section></div>}
  {history&&<div className="modal-backdrop"><section className="modal" role="dialog" aria-modal="true" aria-label="目標修改紀錄"><button aria-label="關閉" onClick={()=>setHistory(null)}>×</button><h2>{history.branch.name}・目標修改紀錄</h2>{history.items.sort((a:Row,b:Row)=>(b.createdAt?.seconds||0)-(a.createdAt?.seconds||0)).map((h:Row)=><div key={h.id}><strong>{h.period} 第 {h.next.revision} 次設定</strong><p>{h.createdAt?.toDate?.().toLocaleString('zh-TW',{timeZone:'Asia/Taipei'})}・操作帳號 UID：{h.by}</p>{['occupancy','performance','referrals'].map(k=><p key={k}>{({occupancy:'出租率',performance:'業績完成率',referrals:'轉介數量'} as Row)[k]}：{h.previous?.[k]??'未設定'} → {h.next[k]??'未設定'}</p>)}<p>其它目標（修改前）</p><OtherGoalResults goals={h.previous?.other}/><p>其它目標（修改後）</p><OtherGoalResults goals={h.next.other}/></div>)}{!history.items.length&&<p>尚無修改紀錄</p>}</section></div>}
 </>;
}
export function VacancyCell({unit,editable}:{unit:Row;editable:boolean}){
 const [open,setOpen]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false);const days=vacantDays(unit,taipeiDate());
 if(unit.status!=='vacant'||unit.missing||unit.archived)return <>—</>;
 return <><span>{unit.vacantSince||'未記錄'}{days!=null&&<small className="table-sub">空置 {days} 天</small>}</span>{editable&&<button className="text-button" onClick={()=>setOpen(!open)}>補填／修改</button>}{open&&<form onSubmit={async e=>{e.preventDefault();setBusy(true);setError('');try{const f=new FormData(e.currentTarget);await saveVacantSince(unit.branchId,unit.code,String(f.get('date')||''));setOpen(false);}catch(err){setError(err instanceof Error?err.message:String(err));}finally{setBusy(false);}}}><input aria-label="空倉起始日" name="date" type="date" max={taipeiDate()} defaultValue={unit.vacantSince||''}/><button disabled={busy}>儲存</button>{error&&<span role="alert">{error}</span>}</form>}</>;
}
export {exitCategories};

export function OperationsInsights({units,events}:{units:Row[];events:Row[]}){
 const today=taipeiDate(),vacant=units.filter(u=>u.status==='vacant'&&!u.archived&&!u.missing),exits=events.filter(e=>e.type==='exit'&&!e.voided);
 return <section className="panel target-panel"><h2>空倉與退租概況</h2><p>空倉 {vacant.length} 間・起始日未記錄 {vacant.filter(u=>vacantDays(u,today)==null).length} 間</p><p>空置至少 30 天：{vacant.filter(u=>(vacantDays(u,today)??-1)>=30).length} 間・至少 60 天：{vacant.filter(u=>(vacantDays(u,today)??-1)>=60).length} 間・至少 90 天：{vacant.filter(u=>(vacantDays(u,today)??-1)>=90).length} 間（區間包含較長天數）</p><h3>所選月份退租原因</h3>{[...exitCategories,'未分類'].map(c=><span key={c} className="badge">{c}：{exits.filter(e=>(e.exitCategory||'未分類')===c).length} 筆 </span>)}</section>;
}

// storeasy-other-monthly-v1

// storeasy-achieved-red-v1

// storeasy-opening-month-v1
