import React,{useEffect,useState} from 'react';
import {collection,onSnapshot,query,where} from 'firebase/firestore';
import {db,call} from './firebase';
import {taipeiDate} from './domain.js';
import {matchingRenewals} from './pending-renewals';

export function PendingEdit({unit}:any){
 const [checked,setChecked]=useState(false);
 const [matches,setMatches]=useState<any[]>([]);
 const [error,setError]=useState('');
 const [loading,setLoading]=useState(false);

 return <div>
  <label style={{display:'flex',alignItems:'center',gap:8}}>
   <input
    style={{width:'auto'}}
    type="checkbox"
    name="markRenewalPending"
    checked={checked}
    onChange={async e=>{
     const enabled=e.target.checked;
     setChecked(enabled);
     setError('');
     if(!enabled)return;
     setLoading(true);
     try{
      const form=e.target.form;
      const period=String(new FormData(form!).get('leasePeriod')||'');
      setMatches(await matchingRenewals(unit.branchId,unit.code,period));
     }catch(err:any){
      setError(err.message);
     }finally{
      setLoading(false);
     }
    }}
   />
   將此租期標記為待收款續約
  </label>
  {checked&&<>
   <p className="hint">
    保留租期，收款確認後才計入續約。若已有相同租期的續約紀錄，會更正該筆；歷史 KPI 不更動。
   </p>
   {loading&&<p>查詢原續約紀錄中…</p>}
   {error&&<p className="danger">{error}</p>}
   {matches.length>1&&<label>
    請選擇要更正的續約紀錄
    <select name="pendingEventId" required defaultValue="">
     <option value="">請選擇</option>
     {matches.map(e=><option key={e.id} value={e.id}>
      {e.date}・統計月份 {e.month}
     </option>)}
    </select>
   </label>}
  </>}
 </div>;
}

function Payment({row,busy,onSave}:any){
 const [open,setOpen]=useState(false);

 return <div style={{borderTop:'1px solid #e3e9f2',padding:'12px 0'}}>
  <strong>{row.branchName}・{row.code}</strong>
  <span style={{marginLeft:12}}>{row.leasePeriod}</span>
  <button
   type="button"
   className="secondary"
   disabled={busy}
   style={{marginLeft:12}}
   onClick={()=>setOpen(v=>!v)}
  >確認收款</button>
  <button
   type="button"
   className="text-button danger"
   disabled={busy}
   style={{marginLeft:12}}
   onClick={()=>{
    if(!window.confirm(`確定刪除 ${row.code} 的這筆待收款？
只移除待收款紀錄，保留目前租期，不變更續約筆數。`))return;
    onSave(
     ()=>call('deletePendingRenewal',{
      branchId:row.branchId,
      pendingId:row.id
     }),
     '待收款紀錄已刪除'
    );
   }}
  >刪除</button>
  {open&&<form onSubmit={e=>{
   e.preventDefault();
   const f=new FormData(e.currentTarget);
   onSave(()=>call('confirmRenewalPayment',{
    branchId:row.branchId,
    pendingId:row.id,
    date:f.get('date'),
    month:f.get('month')
   }),'已確認收款；未匯入 KPI 的月份已計入續約');
  }}>
   <div className="form-grid">
    <label>
     收款日期
     <input type="date" name="date" required max={taipeiDate()} defaultValue={taipeiDate()}/>
    </label>
    <label>
     續約統計月份
     <input type="month" name="month" required defaultValue={taipeiDate().slice(0,7)}/>
    </label>
   </div>
   <p className="hint">
    已有歷史 KPI 的月份只保留收款紀錄，不加計 KPI；不改動目前倉位租期。
   </p>
   <button className="primary" disabled={busy}>確認已收款</button>
  </form>}
 </div>;
}

export function usePendingRenewals(
 branches:any[],
 enabled:boolean,
 onError:(message:string)=>void
){
 const [rows,setRows]=useState<any[]>([]);
 const key=branches.map(b=>b.id+':'+b.name).join('|');

 useEffect(()=>{
  setRows([]);
  if(!enabled)return;
  const buckets=new Map<string,any[]>();
  const stops=branches.map(b=>onSnapshot(
   query(
    collection(db,'branches',b.id,'pendingRenewals'),
    where('status','==','pending')
   ),
   s=>{
    buckets.set(b.id,s.docs.map(d=>({
     id:d.id,...d.data(),branchId:b.id,branchName:b.name
    })));
    setRows(Array.from(buckets.values()).flat());
   },
   e=>onError(e.message)
  ));
  return()=>stops.forEach(stop=>stop());
 },[key,enabled]);

 return rows;
}

export function PendingRenewals({rows,busy,onSave}:any){
 if(!rows.length)return null;
 return <section className="panel" style={{padding:20,marginBottom:16}}>
  <details>
   <summary style={{cursor:'pointer',fontWeight:600}}>
    待收款續約 {rows.length} 筆
   </summary>
   <p className="hint">
    此處會保留所有未確認收款的租期，即使目前倉位已換租期或退租。
   </p>
   {rows.map((row:any)=><Payment
    key={row.branchId+row.id}
    row={row}
    busy={busy}
    onSave={onSave}
   />)}
  </details>
 </section>;
}