
import {createContext,useContext,useEffect,useState} from 'react';
import {collection,onSnapshot,query,where} from 'firebase/firestore';
import {auth,db,call} from './firebase';
import {inventorySignature} from './inventory-diff.js';
import {parseLease} from './lease.js';
import {taipeiDate,validDate} from './domain.js';
import {exitCategories} from './targets.js';
import {leaseTerm} from './lease-term.js';
import './bulk-units.css';

type Row=Record<string,any>;
const id=(u:Row)=>JSON.stringify([u.branchId,u.code]);
const Context=createContext<any>(null);
const can=(u:Row,p:Row)=>u.status==='rented'&&!u.missing&&!u.archived&&(
 ['admin','supervisor'].includes(p.role)||
 p.role==='manager'&&(p.branchIds||[]).includes(u.branchId)
);
const terms:Row={
 monthly:'月繳',quarterly:'季繳',halfYear:'半年繳',
 yearly:'年繳',other:'其他租期',unknown:'租期未提供'
};

function load(key:string){
 try{
  const v=JSON.parse(sessionStorage.getItem(key)||'null');
  return v&&['renew','exit'].includes(v.type)&&Array.isArray(v.rows)?
   {...v,rows:v.rows.map((r:Row)=>r.status==='saving'?
    {...r,status:'failed',message:'上次送出結果尚未確認，請重試核對'}:r)}:
   null;
 }catch{return null;}
}

function ActivityChoices({row,disabled,onChange}:{
 row:Row;disabled:boolean;onChange:(v:string[])=>void
}){
 const [options,setOptions]=useState<Row[]>([]);
 const [error,setError]=useState('');
 useEffect(()=>{
  setOptions([]);setError('');
  if(!validDate(row.date))return;
  return onSnapshot(
   query(
    collection(db,'branches',row.unit.branchId,'activities'),
    where('month','==',row.date.slice(0,7))
   ),
   s=>setOptions(s.docs.map(d=>({...d.data(),id:d.id}))
    .filter((v:Row)=>!v.archived&&!v.deleting)),
   e=>setError(e.message)
  );
 },[row.unit.branchId,row.date.slice(0,7)]);

 return <fieldset disabled={disabled}>
  <legend>使用活動（本次重新選擇）</legend>
  {error&&<p role="alert">{error}</p>}
  {options.map(a=><label className="check-label" key={a.id}>
   <input type="checkbox" checked={row.activityIds.includes(a.id)}
    onChange={e=>onChange(e.target.checked?
     [...row.activityIds,a.id]:
     row.activityIds.filter((v:string)=>v!==a.id)
    )}
   />{a.name}
  </label>)}
  {!options.length&&!error&&<small>此月份沒有可選活動。</small>}
 </fieldset>;
}

function payload(row:Row,type:string){
 if(!validDate(row.date)||row.date>taipeiDate()){
  throw Error('日期請填實際日期，不能晚於今天');
 }
 const data:Row={
  branchId:row.unit.branchId,code:row.unit.code,type,date:row.date,
  operationId:row.operationId,expectedUnit:row.expectedUnit,activityIds:[]
 };
 if(type==='renew'){
  const lease=parseLease(row.leasePeriod);
  if(!lease.leasePeriod)throw Error('請填完整的新租期');
  if(lease.leasePeriod===parseLease(row.unit.leasePeriod||'').leasePeriod){
   throw Error('新租期與原租期相同；補收舊款請使用待收款清單');
  }
  Object.assign(data,{
   leasePeriod:lease.leasePeriod,
   unpaid:row.unpaid?'on':null,
   activityIds:row.activityIds
  });
 }else{
  if(!exitCategories.includes(row.exitCategory)){
   throw Error('請選擇退租原因分類');
  }
  const reason=row.exitReason.trim();
  if(!reason||reason.length>500)throw Error('退租原因請填 1～500 字');
  Object.assign(data,{exitCategory:row.exitCategory,exitReason:reason});
 }
 return data;
}

export function BulkUnitCheck({unit}:{unit:Row}){
 const c=useContext(Context);
 if(!c||!can(unit,c.profile))return null;
 return <input className="bulk-unit-check" type="checkbox"
  aria-label={`勾選倉位 ${unit.branchName} ${unit.code}`}
  checked={c.checked.includes(id(unit))} disabled={c.busy}
  onChange={e=>c.setChecked((v:string[])=>e.target.checked?
   [...v,id(unit)]:v.filter(k=>k!==id(unit))
  )}
 />;
}

export default function BulkUnits({visibleUnits,profile,children}:{
 visibleUnits:Row[];profile:Row;children:React.ReactNode
}){
 const key='storeasy-bulk-units:'+(auth.currentUser?.uid||'');
 const [checked,setChecked]=useState<string[]>([]);
 const [draft,setDraft]=useState<Row|null>(()=>load(key));
 const [open,setOpen]=useState(false);
 const [phase,setPhase]=useState('edit');
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');

 const selectable=visibleUnits.filter(u=>can(u,profile));
 const picked=selectable.filter(u=>checked.includes(id(u)));

 useEffect(()=>{
  const keys=new Set(selectable.map(id));
  setChecked(v=>v.filter(k=>keys.has(k)));
 },[selectable.map(id).join('|')]);

 useEffect(()=>{
  try{
   if(draft)sessionStorage.setItem(key,JSON.stringify(draft));
   else sessionStorage.removeItem(key);
  }catch{}
 },[draft,key]);

 const rows:Row[]=draft?.rows||[];
 const success=rows.filter(r=>r.status==='success').length;
 const failed=rows.filter(r=>r.status==='failed').length;
 const pending=rows.length-success-failed;

 const patch=(operationId:string,value:Row)=>setDraft(v=>v?{
  ...v,rows:v.rows.map((r:Row)=>r.operationId===operationId?{...r,...value}:r)
 }:v);

 function begin(type:string){
  if(!picked.length)return;
  if(draft&&draft.rows.some((r:Row)=>r.status!=='success')){
   setError('尚有未完成批次，請先繼續處理，或清除暫存清單後再建立。');
   return;
  }
  setDraft({
   type,
   rows:picked.map(unit=>({
    unit:{...unit},operationId:'bulk_'+crypto.randomUUID(),
    expectedUnit:inventorySignature(unit),date:taipeiDate(),
    leasePeriod:'',unpaid:false,activityIds:[],
    exitCategory:'',exitReason:'',status:'pending',message:''
   }))
  });
  setPhase('edit');setError('');setOpen(true);
 }

 function review(){
  let invalid=false;setError('');
  for(const row of rows.filter(r=>r.status!=='success')){
   try{
    payload(row,draft!.type);
    patch(row.operationId,{message:''});
   }catch(e){
    invalid=true;
    patch(row.operationId,{message:e instanceof Error?e.message:String(e)});
   }
  }
  if(invalid){
   setError('請先修正各筆標示的資料，再檢查送出。');
   return;
  }
  setPhase('confirm');
 }

 async function send(){
  if(busy||!draft)return;
  setBusy(true);setError('');
  const targets=rows.filter(r=>r.status!=='success');
  const owner=auth.currentUser?.uid;
  for(const row of targets){
   if(auth.currentUser?.uid!==owner){
    setError('登入帳號已變更，已停止未完成項目');
    break;
   }
   patch(row.operationId,{status:'saving',message:''});
   try{
    await call('recordEvent',payload(row,draft.type));
    patch(row.operationId,{status:'success',message:'已完成'});
   }catch(e){
    patch(row.operationId,{
     status:'failed',message:e instanceof Error?e.message:String(e)
    });
   }
  }
  setBusy(false);setPhase('result');setChecked([]);
 }

 function close(){
  if(busy)return;
  setOpen(false);setError('');
  if(rows.every(r=>r.status==='success'))setDraft(null);
 }

 return <Context.Provider value={{checked,setChecked,profile,busy}}>
  {['admin','supervisor','manager'].includes(profile.role)&&
   <div className="bulk-unit-toolbar">
    <label><input type="checkbox" aria-label="全選目前可批次處理倉位"
     disabled={busy||!selectable.length}
     checked={!!selectable.length&&picked.length===selectable.length}
     ref={e=>{if(e)e.indeterminate=picked.length>0&&picked.length<selectable.length;}}
     onChange={e=>setChecked(e.target.checked?selectable.map(id):[])}
    />全選目前清單</label>
    <span>已選取 {picked.length} 間</span>
    <button className="secondary" disabled={!picked.length||busy} onClick={()=>begin('renew')}>批次續約</button>
    <button className="secondary" disabled={!picked.length||busy} onClick={()=>begin('exit')}>批次退租／出倉</button>
    {draft&&<>
     <button className="secondary" onClick={()=>{
      setOpen(true);setPhase('edit');setError('');
     }}>繼續未完成批次</button>
     <button className="text-button" onClick={()=>{
      if(window.confirm('清除暫存清單？已成功的異動會保留，不會撤銷。')){
       setDraft(null);setOpen(false);
      }
     }}>清除暫存清單</button>
    </>}
    <small>僅勾選目前篩選後、有權限操作的已出租倉位；續約與退租分開處理。</small>
   </div>
  }
  {error&&!open&&<p role="alert" className="alert error">{error}</p>}
  {children}

  {open&&draft&&<div className="modal-backdrop">
   <section className="modal wide bulk-unit-modal" role="dialog"
    aria-modal="true"
    aria-label={draft.type==='renew'?'批次續約':'批次退租／出倉'}>
    <div className="modal-heading">
     <h2>{draft.type==='renew'?'批次續約':'批次退租／出倉'} · {rows.length} 間</h2>
     <button aria-label="關閉批次處理" disabled={busy} onClick={close}>← 返回倉位</button>
    </div>
    <div className="bulk-unit-summary" role="status">成功 {success} 筆 · 失敗 {failed} 筆 · 待處理 {pending} 筆</div>
    {error&&<p role="alert" className="alert error">{error}</p>}
    {phase==='confirm'&&<p className="alert success">
     請核對下列資料，本次將送出 {rows.length-success} 筆。
     {draft.type==='renew'?'已付款依收款日期計續約；未付款只列待收款。':'退租會將倉位改為空倉。'}
     成功項目不會再次送出。
    </p>}

    {rows.map(row=>{
     const locked=busy||row.status==='success'||phase==='confirm';
     let term='';
     try{term=terms[leaseTerm(parseLease(row.leasePeriod))]||'';}catch{}
     return <article className={'bulk-unit-card '+row.status} key={row.operationId}>
      <div className="bulk-unit-card-title">
       <strong>{row.unit.branchName} · {row.unit.code}</strong>
       <span>{row.status==='success'?'成功':row.status==='failed'?'失敗':row.status==='saving'?'送出中':'待處理'}</span>
       {!locked&&<button className="text-button" onClick={()=>setDraft(v=>v?{
        ...v,rows:v.rows.filter((r:Row)=>r.operationId!==row.operationId)
       }:v)}>移除此筆</button>}
      </div>
      <p className="hint">原租期：{row.unit.leasePeriod||'未提供'}；月租牌價：NT$ {Number(row.unit.price||0).toLocaleString()}</p>

      <fieldset disabled={locked}><div className="bulk-unit-fields">
       <label>{draft.type==='exit'?'退租日期':row.unpaid?'登記日期':'實際收款日期'}
        <input type="date" aria-label={`${row.unit.code} 異動日期`}
         value={row.date} max={taipeiDate()}
         onChange={e=>patch(row.operationId,{date:e.target.value,activityIds:[]})}
        />
       </label>

       {draft.type==='renew'?<>
        <label>新租期
         <input aria-label={`${row.unit.code} 新租期`}
          placeholder="2026/10/25－2027/01/24" value={row.leasePeriod}
          onChange={e=>patch(row.operationId,{leasePeriod:e.target.value})}
         /><small>{term}</small>
        </label>
        <label>收款狀態
         <select aria-label={`${row.unit.code} 收款狀態`}
          value={row.unpaid?'unpaid':'paid'}
          onChange={e=>patch(row.operationId,{unpaid:e.target.value==='unpaid'})}>
          <option value="paid">已付款</option>
          <option value="unpaid">未付款／待收款</option>
         </select>
         <small>{row.unpaid?'不計續約；已開始的未付款租期列逾期':`計入 ${row.date.slice(0,7)} 續約`}</small>
        </label>
       </>:<>
        <label>退租原因分類
         <select aria-label={`${row.unit.code} 退租原因分類`}
          value={row.exitCategory}
          onChange={e=>patch(row.operationId,{exitCategory:e.target.value})}>
          <option value="">請選擇</option>
          {exitCategories.map(c=><option key={c}>{c}</option>)}
         </select>
        </label>
        <label>退租原因
         <textarea aria-label={`${row.unit.code} 退租原因`}
          maxLength={500} value={row.exitReason}
          onChange={e=>patch(row.operationId,{exitReason:e.target.value})}
         />
        </label>
       </>}
      </div></fieldset>

      {draft.type==='renew'&&<ActivityChoices row={row} disabled={locked}
       onChange={activityIds=>patch(row.operationId,{activityIds})}/>}
      {row.message&&<p role={row.status==='success'?'status':'alert'}
       className={row.status==='success'?'hint':'danger'}>{row.message}</p>}
     </article>;
    })}

    <div className="bulk-unit-footer">
     {phase==='confirm'?<>
      <button className="secondary" disabled={busy} onClick={()=>setPhase('edit')}>返回修改</button>
      <button className="primary" disabled={busy||rows.length===success} onClick={send}>
       {busy?'正在逐筆處理…':`確認送出 ${rows.length-success} 筆`}
      </button>
     </>:<button className="primary"
      disabled={busy||!rows.length||rows.length===success} onClick={review}>
      {failed?'檢查未完成項目並重試':'檢查並準備送出'}
     </button>}
     <button className="secondary" disabled={busy} onClick={close}>
      {rows.length===success?'完成並返回':'關閉並保留清單'}
     </button>
    </div>
   </section>
  </div>}
 </Context.Provider>;
}
