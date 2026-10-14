import React,{useState} from 'react';
import {taipeiDate} from './domain.js';

export default function TransferForm({unit,type,units,busy,onSave,onDateChange}:any){
 const [mode,setMode]=useState('local');
 const available=units.filter((u:any)=>
  u.branchId===unit.branchId&&u.code!==unit.code
  &&u.status==='vacant'&&!u.leasePeriod&&!u.missing&&!u.archived
 );
 return <form onSubmit={e=>{
  e.preventDefault();
  const f=new FormData(e.currentTarget);
  onSave({
   branchId:unit.branchId,code:unit.code,type,mode,
   date:f.get('date'),targetCode:f.get('targetCode'),
   leasePeriod:f.get('leasePeriod')
  });
 }}>
  <p><strong>{unit.code}</strong> · {unit.branchName}</p>
  <label>異動日期
   <input name="date" type="date" required defaultValue={taipeiDate()} max={taipeiDate()} onChange={e=>onDateChange(e.target.value.slice(0,7))}/>
  </label>
  {type==='transferOut'&&<label>轉出方式
   <select value={mode} onChange={e=>setMode(e.target.value)}>
    <option value="local">同據點轉倉</option>
    <option value="external">轉至其它據點</option>
   </select>
  </label>}
  {type==='transferOut'&&mode==='local'&&<label>目的空倉
   <select name="targetCode" required defaultValue="">
    <option value="" disabled>請選擇現有空倉</option>
    {available.map((u:any)=><option key={u.code} value={u.code}>{u.code} · {u.dimensions}</option>)}
   </select>
   {!available.length&&<small>目前沒有可轉入的空倉。</small>}
  </label>}
  {(type==='transferIn'||mode==='local')&&<label>新租期
   <input aria-label="新租期" name="leasePeriod" required placeholder="2026/10/08－2027/04/07" autoComplete="off"/>
   <small>請輸入完整起訖日期，例如 2026/10/08－2027/04/07。</small>
  </label>}
  <p className="hint">
   {type==='transferOut'&&mode==='external'
    ?'儲存後原倉位變空倉；目的據點的店長再於空倉登記「轉入」，不需要查詢或選擇其它據點的倉位。'
    :type==='transferOut'
     ?'儲存後原倉位變空倉，目的倉位套用新租期。'
     :'儲存後此倉位套用新租期，變為已出租。'
   }轉倉不計入新承租或退租。
  </p>
  <button className="primary submit" disabled={busy||type==='transferOut'&&mode==='local'&&!available.length}>
   {busy?'儲存中…':'確認儲存'}
  </button>
 </form>;
}

// storeasy-transfers-v1
