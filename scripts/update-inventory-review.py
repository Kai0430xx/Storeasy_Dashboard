from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
MARK='storeasy-inventory-review-v1'
prepared={}

def sub(s,pattern,value):
    s,n=re.subn(pattern,lambda m:value(m) if callable(value) else value,s)
    if n!=1:
        raise RuntimeError('版本不符，未寫入任何檔案：'+pattern[:90])
    return s

p=ROOT/'src/main.tsx'
s=p.read_text(encoding='utf-8')
if MARK not in s:
    s='import InventoryReview from "./InventoryReview";\n'+s
    s=sub(
        s,
        r'units=\{data\[modal.branchId\]\?\.units \|\| \[\]\}',
        'units={data[modal.branchId]?.units || []} months={data[modal.branchId]?.months || []}'
    )
    s=sub(
        s,
        r'\?\s*"importInventory"',
        '? payload.reviewDiff ? "reviewInventory" : "importInventory"'
    )
    s=sub(
        s,
        r'function ImportForm\(\{',
        'function ImportForm(props:any){return props.kind==="inventory"?<InventoryReview {...props}/>:<LegacyImportForm {...props}/>;}\nfunction LegacyImportForm({'
    )
    s=sub(
        s,
        r'盤點不計入新承租／退租業績',
        '全部匯入覆蓋現況；僅匯入差異可逐筆確認異動與月份'
    )
    prepared['src/main.tsx']=s

p=ROOT/'src/api.ts'
s=p.read_text(encoding='utf-8')
if MARK not in s:
    s='import {reviewInventory} from "./review-inventory";\n'+s
    s=sub(
        s,
        r'case "importInventory": \{',
        'case "reviewInventory": return reviewInventory(data);\n    case "importInventory": {'
    )
    prepared['src/api.ts']=s

p=ROOT/'firestore.rules'
s=p.read_text(encoding='utf-8')
if MARK not in s:
    start=s.index('match /events/{eventId}')
    end=s.index('match /activities/{activityId}',start)
    block=s[start:end]
    block=sub(
        block,
        r'match /events/\{eventId\} \{',
        """match /events/{eventId} {
    function reviewedImport() {
     let b=get(/databases/$(database)/documents/branches/$(id)).data;
     return 'importing' in b && b.importing.operation=='reviewInventory' && b.importing.by==request.auth.uid
      && request.resource.data.importRun==b.importing.token;
    }
"""
    )
    block=sub(
        block,
        r'allow create: if branchEdit\(id\)\s*&& unlocked\(id\)',
        'allow create: if branchEdit(id) && (unlocked(id) || reviewedImport())'
    )
    block=sub(
        block,
        r'let before=get\(/databases/\$\(database\)/documents/branches/\$\(id\)/units/\$\(e.code\)\).data;',
        "let before=exists(/databases/$(database)/documents/branches/$(id)/units/$(e.code)) ? get(/databases/$(database)/documents/branches/$(id)/units/$(e.code)).data : {'status':'vacant'};"
    )
    s=s[:start]+block+s[end:]
    prepared['firestore.rules']=s

TEXT = r"""import {normalizeUnits} from './domain.js';
import {parseLease} from './lease.js';

const fields=['dimensions','volume','price','unitPrice','note','leasePeriod','status','missing','archived'];
export const inventoryFieldLabels={
 dimensions:'尺寸',volume:'材積',price:'月租',unitPrice:'單價',
 note:'備註',leasePeriod:'租期',status:'出租狀態',
 missing:'清單狀態',archived:'封存狀態'
};

function comparable(row){
 const lease=parseLease(row.leasePeriod||'');
 return {
  dimensions:String(row.dimensions||''),
  volume:Number(row.volume||0),
  price:Number(row.price||0),
  unitPrice:Number(row.unitPrice||0),
  note:String(row.note||''),
  leasePeriod:lease.leasePeriod,
  status:row.status||'vacant',
  missing:Boolean(row.missing),
  archived:Boolean(row.archived)
 };
}

export function inventorySignature(row){
 if(!row)return null;
 return JSON.stringify([
  comparable(row),row.leaseStart||null,row.leaseEnd||null,
  row.vacantSince||null,row.lastEventId||null,
  row.lastEventDate||null,row.priceEffectiveDate||null,
  row.priceHistory||[]
 ]);
}

export function compareInventory(incoming,existing){
 const normalized=normalizeUnits(incoming),old=new Map();
 for(const row of existing){
  if(old.has(row.code))throw new Error('既有倉位編號重複，無法比對：'+row.code);
  old.set(row.code,row);
 }
 const codes=new Set(normalized.map(row=>row.code));
 const rows=normalized.map(row=>{
  const before=old.get(row.code)||null;
  const after={
   ...row,status:row.leasePeriod?'rented':'vacant',
   missing:false,archived:false
  };
  const left=before?comparable(before):null,right=comparable(after);
  const changed=left?fields.filter(key=>left[key]!==right[key]):fields;
  return {
   code:row.code,before,after,changed,
   signature:inventorySignature(before),isNew:!before
  };
 });
 return {
  rows,
  differences:rows.filter(row=>row.changed.length>0),
  unchanged:rows.filter(row=>!row.changed.length),
  missing:existing.filter(row=>!row.archived&&!codes.has(row.code))
 };
}

export function inventoryMonths(today){
 const y=Number(today.slice(0,4)),m=Number(today.slice(5,7));
 return [-1,0,1].map(offset=>{
  const d=new Date(Date.UTC(y,m-1+offset,1));
  return d.toISOString().slice(0,7);
 });
}

export function suggestedInventoryAction(row){
 if(!row.before||row.before.missing||row.before.archived)return 'sync';
 if(row.before.status==='rented'&&row.after.status==='vacant')return 'exit';
 if(row.before.status==='vacant'&&row.after.status==='rented')return 'new';
 if(row.before.status==='rented'&&row.after.status==='rented'&&row.changed.includes('leasePeriod'))return 'renew';
 return 'sync';
}

export function validateInventoryChange(before,after,change,today){
 const type=change.type;
 if(!['new','renew','exit','transferIn','transferOut','sync'].includes(type))
  throw new Error('請選擇異動類型');
 if(!inventoryMonths(today).includes(change.month))
  throw new Error('請選擇上個月、本月或下個月');
 const oldRented=before?.status==='rented',rented=Boolean(after.leasePeriod);
 if(
  (['new','transferIn'].includes(type)&&(oldRented||!rented))
  ||(type==='renew'&&(!oldRented||!rented))
  ||(['exit','transferOut'].includes(type)&&(!oldRented||rented))
 )throw new Error('異動類型與原倉位、新租期不一致');
 if(type==='renew'&&parseLease(before.leasePeriod||'').leasePeriod===after.leasePeriod)
  throw new Error('續約的新租期必須與原租期不同');
 if(type==='exit'&&(
  !['價格','距離','不再需要','改租其它倉位/據點','服務或環境','其它'].includes(change.exitCategory)
  ||!String(change.exitReason||'').trim()
  ||String(change.exitReason).trim().length>500
 ))throw new Error('退租請選原因分類，並填寫1～500字的原因');
}
"""
name='src/inventory-diff.js'
p=ROOT/name
if p.exists() and MARK not in p.read_text(encoding='utf-8'):
    raise RuntimeError(name+' 已存在不同版本，未寫入任何檔案')
if not p.exists():
    prepared[name]=TEXT

TEXT = r"""import {
 collection,doc,getDoc,getDocs,query,where,documentId,
 runTransaction,serverTimestamp,deleteField
} from 'firebase/firestore';
import {auth,db} from './firebase';
import {normalizeUnits,validDate,taipeiDate,inventoryStats} from './domain.js';
import {inventorySignature,validateInventoryChange} from './inventory-diff.js';
import {pricingUpdate,priceSnapshot} from './pricing.js';
import {vacancyDate} from './targets.js';
import {sourceFiles} from './import-actions';

const time=()=>serverTimestamp();

export async function reviewInventory(data:any){
 const uid=auth.currentUser?.uid;
 if(!uid)throw new Error('請先登入');
 if(typeof data.branchId!=='string'||!data.branchId||data.branchId.includes('/'))
  throw new Error('據點不合法');
 if(!/^[a-zA-Z0-9-]{8,80}$/.test(data.reviewId))
  throw new Error('請重新分析匯入檔案');
 if(!validDate(data.effectiveDate)||data.effectiveDate>taipeiDate())
  throw new Error('盤點日期不合法');
 const files=sourceFiles(data,'inventory');
 if(!Array.isArray(data.changes)||data.changes.length>10000)
  throw new Error('差異資料不合法');
 if(!data.changes.length)return {};

 const normalized=normalizeUnits(data.changes.map((c:any)=>c.after));
 const jobs=data.changes.map((c:any,i:number)=>({
  ...c,after:normalized[i],
  exitReason:String(c.exitReason||'').trim(),
  date:c.date||data.effectiveDate
 }));
 for(const job of jobs){
  if(!validDate(job.date)||job.date>taipeiDate())
   throw new Error(job.after.code+'：異動日期不合法');
  validateInventoryChange(job.before,job.after,job,taipeiDate());
 }

 const branch=doc(db,'branches',data.branchId),token=data.reviewId;
 if((await getDoc(doc(branch,'imports',token))).exists())return {};
 let locked=false,completed=0;

 try{
  await runTransaction(db,async tx=>{
   const s=await tx.get(branch);
   if(!s.exists())throw new Error('據點不存在');
   const b=s.data();
   if(b.importing&&Date.now()-b.importing.startedAt<600000)
    throw new Error('據點有其它匯入正在執行，請稍後再試');
   if(b.inventoryDate&&data.effectiveDate<b.inventoryDate)
    throw new Error('盤點日期不得早於上次盤點');
   tx.update(branch,{
    importing:{operation:'reviewInventory',token,by:uid,startedAt:Date.now()},
    revision:b.revision+1
   });
  });
  locked=true;

  const current=new Map<string,any>();
  for(let i=0;i<jobs.length;i+=30){
   const s=await getDocs(query(
    collection(branch,'units'),
    where(documentId(),'in',jobs.slice(i,i+30).map((j:any)=>j.after.code))
   ));
   for(const d of s.docs)current.set(d.id,d.data());
  }

  const jobKey=(job:any)=>JSON.stringify([
   job.after,job.type,job.month,job.date,
   job.exitCategory||'',job.exitReason,data.effectiveDate
  ]);
  const done=(old:any,job:any)=>
   old?.reviewImport?.id===token
   &&old.reviewImport.key===jobKey(job)
   &&inventorySignature(old)===old.reviewImport.after;

  for(const job of jobs){
   const old=current.get(job.after.code);
   if(old?.reviewImport?.id===token){
    if(!done(old,job))
     throw new Error(job.after.code+'：上次已匯入，內容已改變，請重新分析');
   }else if(inventorySignature(old)!==job.signature){
    throw new Error(job.after.code+'：分析後倉位已被修改，請重新分析');
   }
   if(!done(old,job)){
    validateInventoryChange(old,job.after,job,taipeiDate());
    if(old?.lastEventDate&&job.date<old.lastEventDate)
     throw new Error(job.after.code+'：日期不得早於上一筆異動');
    const pricing=pricingUpdate(old,job.after,data.effectiveDate,null);
    if(job.type!=='sync')priceSnapshot({...job.after,...pricing},job.date);
   }
  }

  for(const job of jobs){
   const unit=doc(branch,'units',job.after.code);
   const month=doc(branch,'months',job.month);
   const nowMonth=doc(branch,'months',taipeiDate().slice(0,7));
   const event=doc(branch,'events','review_'+token+'_'+encodeURIComponent(job.after.code));

   await runTransaction(db,async tx=>{
    const [bs,us,ms,ns]=await Promise.all([
     tx.get(branch),tx.get(unit),tx.get(month),tx.get(nowMonth)
    ]);
    const b=bs.data(),old=us.data();
    if(!b||b.importing?.token!==token||b.importing.by!==uid)
     throw new Error('匯入鎖定已變更');
    if(done(old,job))return;
    if(inventorySignature(old)!==job.signature)
     throw new Error(job.after.code+'：倉位已被修改，請重新分析');
    validateInventoryChange(old,job.after,job,taipeiDate());

    const status=job.after.leasePeriod?'rented':'vacant';
    const record=job.type!=='sync';
    const next:any={
     ...old,...job.after,
     ...pricingUpdate(old,job.after,data.effectiveDate,null),
     status,missing:false,archived:false,
     vacantSince:vacancyDate(old,status,job.date),
     updatedAt:time()
    };
    if(record){
     next.lastEventDate=job.date;
     next.lastEventId=event.id;
    }else{
     next.lastEventId=old?.lastEventId||null;
     next.lastEventDate=old?.lastEventDate||null;
    }

    const beforeStats=old&&!old.missing&&!old.archived
     ?inventoryStats([old]):{total:0,rented:0,vacant:0};
    const total=b.total+1-beforeStats.total;
    const rented=b.rented+(status==='rented'?1:0)-beforeStats.rented;
    const vacant=b.vacant+(status==='vacant'?1:0)-beforeStats.vacant;
    if(Math.min(total,rented,vacant)<0||total!==rented+vacant)
     throw new Error('據點統計不一致，請先核對倉位資料');

    next.reviewImport={id:token,key:jobKey(job),after:inventorySignature(next)};
    tx.set(unit,next);

    if(record){
     const price=priceSnapshot(next,job.date);
     tx.set(event,{
      code:job.after.code,type:job.type,date:job.date,month:job.month,
      activities:[],
      exitCategory:job.type==='exit'?job.exitCategory:'',
      exitReason:job.type==='exit'?job.exitReason:'',
      priceSnapshot:price,
      unitSnapshot:{
       dimensions:next.dimensions,volume:next.volume,
       price:price.price,note:next.note,
       leasePeriod:next.leasePeriod,leaseStart:next.leaseStart,
       leaseEnd:next.leaseEnd
      },
      previousLease:{
       leasePeriod:old?.leasePeriod||'',
       leaseStart:old?.leaseStart||null,
       leaseEnd:old?.leaseEnd||null,
       vacantSince:old?.vacantSince||null
      },
      previousEventId:old?.lastEventId||null,
      previousEventDate:old?.lastEventDate||null,
      createdBy:uid,createdAt:time(),voided:false,
      importRun:token,importSource:files.total,
      kpiCounted:ms.data()?.source!=='import',
      ...(['transferIn','transferOut'].includes(job.type)?{
       transferMode:'external',transferGroup:event.id,
       peerCode:'',peerEventId:''
      }:{})
     });
     if(ms.data()?.source!=='import'){
      tx.set(month,{
       source:'live',
       [job.type]:(ms.data()?.[job.type]||0)+1,
       updatedAt:time()
      },{merge:true});
     }
    }
    if(ns.data()?.source!=='import'){
     tx.set(nowMonth,{
      source:'live',total,rented,vacant,
      snapshotDate:taipeiDate(),updatedAt:time()
     },{merge:true});
    }
    tx.update(branch,{
     total,rented,vacant,revision:b.revision+1,
     importing:{...b.importing,startedAt:Date.now()},
     updatedAt:time()
    });
   });
   completed++;
  }

  await runTransaction(db,async tx=>{
   const bs=await tx.get(branch),b=bs.data();
   if(!b||b.importing?.token!==token)throw new Error('匯入鎖定已變更');
   tx.update(branch,{
    inventoryDate:data.effectiveDate,
    inventorySource:{...files,id:token,mode:'differences'},
    importing:deleteField(),revision:b.revision+1,updatedAt:time()
   });
   tx.set(doc(branch,'imports',token),{
    total:b.total,rented:b.rented,vacant:b.vacant,
    files,effectiveDate:data.effectiveDate,mode:'differences',
    changedCodes:jobs.map((j:any)=>j.after.code),
    by:uid,createdAt:time()
   });
  });
  locked=false;
  return {};
 }catch(e:any){
  throw new Error(`已完成 ${completed} 筆差異，其餘尚未完成：${e.message}。可重試相同內容，或重新分析；已完成的異動不會重複加計。`);
 }finally{
  if(locked){
   await runTransaction(db,async tx=>{
    const s=await tx.get(branch);
    if(s.data()?.importing?.token===token)
     tx.update(branch,{importing:deleteField()});
   }).catch(()=>{});
  }
 }
}
"""
name='src/review-inventory.ts'
p=ROOT/name
if p.exists() and MARK not in p.read_text(encoding='utf-8'):
    raise RuntimeError(name+' 已存在不同版本，未寫入任何檔案')
if not p.exists():
    prepared[name]=TEXT

TEXT = r"""import React,{useState} from 'react';
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
"""
name='src/InventoryReview.tsx'
p=ROOT/name
if p.exists() and MARK not in p.read_text(encoding='utf-8'):
    raise RuntimeError(name+' 已存在不同版本，未寫入任何檔案')
if not p.exists():
    prepared[name]=TEXT

TEXT = r""".inventory-review .inventory-difference{border:1px solid #dce5f1;border-radius:9px;padding:14px;margin:12px 0;background:#fff}
.inventory-review .difference-heading{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.inventory-review .difference-heading>span{font-size:12px;color:#657793;flex:1}
.inventory-review .difference-heading label,.inventory-review .review-select-all{display:flex;flex-direction:row;gap:8px;align-items:center;margin:0}
.inventory-review input[type=checkbox]{width:18px;height:18px;margin:0;flex:0 0 18px}
.inventory-review .difference-heading select{width:auto;min-width:145px;margin:0}
.inventory-review .difference-comparison{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:12px 0;padding:12px;background:#f6f8fc;border-radius:7px}
.inventory-review .difference-comparison p{margin:6px 0;overflow-wrap:anywhere}
.inventory-review details>summary{cursor:pointer;color:#173f75;padding:7px 0}
.inventory-review .review-edit-fields{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding-top:10px}
.inventory-review .review-wide{grid-column:1/-1}
.inventory-review .review-buttons{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:16px 0}
.inventory-review .review-buttons button{margin:0}
.inventory-review .review-month-batch{margin-top:18px;border:1px solid #dce5f1;border-radius:8px;padding:14px}
.inventory-review .review-month-batch label{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.inventory-review .review-month-batch select{width:auto;margin:0}
.inventory-review .review-change-value{display:block;overflow-wrap:anywhere;margin-top:5px}
@media(max-width:600px){
.inventory-review .review-edit-fields,.inventory-review .difference-comparison{grid-template-columns:1fr}
.inventory-review .difference-heading>label:last-child{width:100%}
}
"""
name='src/inventory-review.css'
p=ROOT/name
if p.exists() and MARK not in p.read_text(encoding='utf-8'):
    raise RuntimeError(name+' 已存在不同版本，未寫入任何檔案')
if not p.exists():
    prepared[name]=TEXT

for name,text in prepared.items():
    marker='\n/* '+MARK+' */\n' if name.endswith('.css') else '\n// '+MARK+'\n'
    (ROOT/name).write_text(text+marker,encoding='utf-8')
    print('已更新 '+name)

print('完成。請將 GitHub 最新 firestore.rules 全文發布到 Firebase。')
