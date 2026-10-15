import React,{useState} from 'react';
import {
 compareInventory,inventoryMonths,inventoryFieldLabels,
 suggestedInventoryAction,validateInventoryChange
} from './inventory-diff.js';
import {normalizeUnits,taipeiDate,validDate} from './domain.js';
import {exitCategories} from './targets.js';
import './inventory-review.css';

const names:any={
 sync:'資料修正／盤點（不計異動）',
 new:'承租',renew:'續約',exit:'退租',
 transferIn:'轉入',transferOut:'轉出'
};
const display=(v:any)=>
 v==null||v===''?'—':typeof v==='boolean'?(v?'是':'否'):String(v);
const monthName=(m:string)=>`${m.slice(0,4)}年${Number(m.slice(5))}月`;

export default function InventoryReview({units,busy,onSubmit,onError,months=[]}:any){
 const [preview,setPreview]=useState<any>(null);
 const [reading,setReading]=useState(false);
 const [drafts,setDrafts]=useState<Record<string,any>>({});
 const [selected,setSelected]=useState<string[]>([]);
 const [batchMonth,setBatchMonth]=useState(taipeiDate().slice(0,7));
 const [page,setPage]=useState(0);
 const choices=inventoryMonths(taipeiDate());
 const change=(code:string,patch:any)=>setDrafts(prev=>({
  ...prev,[code]:{...prev[code],...patch}
 }));
 const all=preview?.rows.map((r:any)=>drafts[r.code]?.after||r.after)||[];
 const codes=preview?.differences.map((r:any)=>r.code)||[];
 const rented=all.filter((u:any)=>String(u.leasePeriod||'').trim()).length;

 const save=(differenceOnly:boolean)=>{
  try{
   const normalized=normalizeUnits(all);
   const changes=preview.differences.map((row:any)=>{
    const d=drafts[row.code];
    const after=normalized.find((u:any)=>u.code===row.code)!;
    if(differenceOnly&&(!validDate(d.date)||d.date>taipeiDate()))
     throw new Error(row.code+'：異動日期不合法');
    if(differenceOnly){
     try{validateInventoryChange(row.before,after,d,taipeiDate());}
     catch(e:any){throw new Error(row.code+'：'+e.message);}
    }
    return {...d,after,before:row.before,signature:row.signature};
   });
   if(!differenceOnly&&!window.confirm(
    '全部匯入將依整份檔案覆蓋倉位現況，檔案未列出的舊倉位會保留並標示清單中消失；不另外加計承租、續約或退租筆數。確定繼續？'
   ))return;
   onError('');
   onSubmit(differenceOnly?{
    reviewDiff:true,reviewId:preview.id,totalFile:preview.filename,
    effectiveDate:preview.date,changes
   }:{
    units:normalized,
    vacantCodes:normalized.filter((u:any)=>!u.leasePeriod).map((u:any)=>u.code),
    totalFile:preview.filename,effectiveDate:preview.date
   });
  }catch(e:any){onError(e.message||String(e));}
 };

 return <div className="inventory-review">
  <form onSubmit={async e=>{
   e.preventDefault();
   const f=new FormData(e.currentTarget);
   setReading(true);onError('');setPreview(null);
   try{
    const {workbook,parseUnits}=await import('./imports');
    const file=f.get('all') as File;
    const rows=parseUnits(
     await workbook(await file.arrayBuffer()),undefined,
     {requirePrice:true,requireLease:true}
    );
    const comparison=compareInventory(rows,units);
    const date=String(f.get('date'));
    const edits=Object.fromEntries(comparison.differences.map((r:any)=>[
     r.code,{
      after:r.after,type:suggestedInventoryAction(r),
      month:taipeiDate().slice(0,7),date,exitCategory:'',exitReason:''
     }
    ]));
    setDrafts(edits);
    setSelected(comparison.differences.map((r:any)=>r.code));
    setBatchMonth(taipeiDate().slice(0,7));
    setPage(0);
    setPreview({...comparison,id:crypto.randomUUID(),date,filename:file.name});
   }catch(e:any){onError(e.message||String(e));}
   finally{setReading(false);}
  }}>
   <label>倉位 Excel
    <input name="all" type="file" accept=".xlsx" required disabled={busy} onChange={()=>setPreview(null)}/>
   </label>
   <label>盤點／新價格生效日期
    <input name="date" type="date" defaultValue={taipeiDate()} max={taipeiDate()} required disabled={busy} onChange={()=>setPreview(null)}/>
   </label>
   <button className="secondary" disabled={busy||reading}>
    {reading?'讀取中…':'分析並預覽'}
   </button>
  </form>

  {preview&&<>
   <h3>匯入比對結果</h3>
   <div className="preview-counts">
    <span>總倉 <b>{all.length}</b></span>
    <span>已出租 <b>{rented}</b></span>
    <span>空倉 <b>{all.length-rented}</b></span>
   </div>
   <p>倉位表：{preview.filename}・差異 {codes.length} 筆，相同 {preview.unchanged.length} 筆。</p>
   {preview.missing.length>0&&<p className="hint">
    檔案未列出：{preview.missing.map((r:any)=>r.code).join('、')}。
    全部匯入會保留並標示清單中消失；僅匯入差異時不更動這些倉位。
   </p>}

   <h3>與既有資料不同的倉位</h3>
   {!codes.length?<p>沒有差異，無需更新倉位。</p>:<>
    <p className="hint">
     下列差異全部會匯入。勾選僅用於批次指定月份，不是排除匯入。
     新增倉位預設盤點；已有倉位的租期、狀態變更會預設對應異動。
    </p>
    <label className="review-select-all">
     <input
      type="checkbox" aria-label="全選差異月份設定"
      checked={selected.length===codes.length} disabled={busy}
      onChange={e=>setSelected(e.target.checked?codes:[])}
     />
     全選／取消全選（含其他頁，共 {codes.length} 筆）
    </label>

    {preview.differences.slice(page*30,(page+1)*30).map((row:any)=>{
     const d=drafts[row.code];
     const update=(key:string,value:any)=>change(row.code,{
      after:{...d.after,[key]:value}
     });
     const extra=row.changed.filter((k:string)=>
      !['leasePeriod','status','price','dimensions'].includes(k)
     );
     return <article className="inventory-difference" key={row.code} data-code={row.code}>
      <div className="difference-heading">
       <label>
        <input
         type="checkbox" aria-label={`勾選 ${row.code} 指定月份`}
         checked={selected.includes(row.code)} disabled={busy}
         onChange={e=>setSelected(prev=>
          e.target.checked?[...prev,row.code]:prev.filter(c=>c!==row.code)
         )}
        />
        <strong>{row.code}</strong>
       </label>
       <span>{row.isNew?'新增倉位':row.changed.map((k:string)=>(inventoryFieldLabels as any)[k]).join('、')}</span>
       <label>統計月份
        <select
         aria-label={`倉位 ${row.code} 的統計月份`}
         value={d.month} disabled={busy}
         onChange={e=>change(row.code,{month:e.target.value})}
        >
         {choices.map((m:string)=><option key={m} value={m}>{monthName(m)}</option>)}
        </select>
       </label>
      </div>

      <div className="difference-comparison">
       <div>
        <small>原資料</small>
        <p>{!row.before?'尚無此倉位':row.before.leasePeriod||'空倉'}</p>
        <small>月租 {row.before?.price??'—'}・尺寸 {row.before?.dimensions||'—'}</small>
        {extra.map((k:string)=><small className="review-change-value" key={k}>
         {(inventoryFieldLabels as any)[k]}：{display(row.before?.[k])}
        </small>)}
       </div>
       <div>
        <small>匯入後</small>
        <p>{d.after.leasePeriod||'空倉'}</p>
        <small>{names[d.type]}・月租 {d.after.price}・尺寸 {d.after.dimensions||'—'}</small>
        {extra.map((k:string)=><small className="review-change-value" key={k}>
         {(inventoryFieldLabels as any)[k]}：{display(d.after[k])}
        </small>)}
       </div>
      </div>

      {months.some((m:any)=>(m.id||m.month)===d.month&&m.source==='import')&&
       <p className="hint">{monthName(d.month)}已有歷史 KPI：只更新現況與紀錄，不加計 KPI 筆數。</p>
      }

      <details open={d.type==='exit'||undefined}>
       <summary>編輯此筆差異</summary>
       <div className="review-edit-fields">
        <label>異動類型
         <select
          aria-label={`倉位 ${row.code} 的異動類型`}
          value={d.type} disabled={busy}
          onChange={e=>{
           const type=e.target.value;
           change(row.code,{
            type,after:{
             ...d.after,
             leasePeriod:['exit','transferOut'].includes(type)?'':
              d.after.leasePeriod||row.after.leasePeriod||row.before?.leasePeriod||''
            }
           });
          }}
         >
          {(row.before?.status==='rented'
           ?['renew','exit','transferOut','sync']
           :['new','transferIn','sync']
          ).map(type=><option key={type} value={type}>{names[type]}</option>)}
         </select>
        </label>
        <label>異動日期
         <input type="date" value={d.date} max={taipeiDate()} disabled={busy} onChange={e=>change(row.code,{date:e.target.value})}/>
        </label>
        {!['exit','transferOut'].includes(d.type)&&<label className="review-wide">新租期
         <input
          aria-label={`倉位 ${row.code} 的新租期`}
          value={d.after.leasePeriod||''} disabled={busy}
          placeholder="2026/10/08－2027/04/07"
          onChange={e=>update('leasePeriod',e.target.value)}
         />
        </label>}
        {d.type==='exit'&&<>
         <label>退租原因分類
          <select
           aria-label={`倉位 ${row.code} 的退租原因分類`}
           value={d.exitCategory} disabled={busy}
           onChange={e=>change(row.code,{exitCategory:e.target.value})}
          >
           <option value="">請選擇</option>
           {exitCategories.map(c=><option key={c}>{c}</option>)}
          </select>
         </label>
         <label className="review-wide">退租原因
          <textarea
           aria-label={`倉位 ${row.code} 的退租原因`}
           maxLength={500} value={d.exitReason} disabled={busy}
           onChange={e=>change(row.code,{exitReason:e.target.value})}
          />
         </label>
        </>}
        <label>尺寸
         <input value={d.after.dimensions} disabled={busy} maxLength={100} onChange={e=>update('dimensions',e.target.value)}/>
        </label>
        {(['volume','price','unitPrice'] as const).map(k=><label key={k}>
         {{volume:'材積',price:'月租',unitPrice:'單價'}[k]}
         <input type="number" min="0" step="any" value={d.after[k]} disabled={busy} onChange={e=>update(k,e.target.value)}/>
        </label>)}
        <label className="review-wide">備註
         <textarea value={d.after.note} disabled={busy} maxLength={500} onChange={e=>update('note',e.target.value)}/>
        </label>
       </div>
      </details>
     </article>;
    })}

    {codes.length>30&&<div className="review-buttons">
     <button disabled={busy||page===0} onClick={()=>setPage(p=>p-1)}>上一頁</button>
     <span>{page+1}／{Math.ceil(codes.length/30)}</span>
     <button disabled={busy||(page+1)*30>=codes.length} onClick={()=>setPage(p=>p+1)}>下一頁</button>
    </div>}

    <fieldset className="review-month-batch">
     <legend>指定勾選資料的倉位變更月份</legend>
     <label>以上勾選的 {selected.length} 筆資料皆匯入
      <select aria-label="批次統計月份" value={batchMonth} disabled={busy} onChange={e=>setBatchMonth(e.target.value)}>
       {choices.map((m:string)=><option key={m} value={m}>{monthName(m)}</option>)}
      </select>
      的倉位變更
     </label>
     <button
      disabled={busy||!selected.length}
      onClick={()=>setDrafts(prev=>Object.fromEntries(
       Object.entries(prev).map(([code,d])=>[
        code,selected.includes(code)?{...d,month:batchMonth}:d
       ])
      ))}
     >套用月份至勾選資料</button>
    </fieldset>
   </>}

   <p className="hint">
    統計月份決定異動筆數歸屬；盤點／異動日期用於現況、價格及空倉起始日。
    資料修正、轉入與轉出不計入新承租／退租。
   </p>
   <div className="review-buttons">
    <button className="primary submit" disabled={busy} onClick={()=>save(false)}>
     {busy?'正在匯入…':'全部匯入（覆蓋現況）'}
    </button>
    <button className="secondary" disabled={busy||!codes.length} onClick={()=>save(true)}>
     僅匯入差異倉位
    </button>
   </div>
  </>}
 </div>;
}

// storeasy-inventory-review-v1
