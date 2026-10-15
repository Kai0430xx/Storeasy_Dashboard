from pathlib import Path
import ast, re

TOKEN = re.compile(r"//[^\n]*|/\*[\s\S]*?\*/|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|[A-Za-z_$][\w$]*|[0-9]+|[^\s]", re.UNICODE)

def tokens(text):
    rows = [
        m for m in TOKEN.finditer(text)
        if not m.group().startswith(("//", "/*"))
    ]
    rows = [
        m for i, m in enumerate(rows)
        if not (
            m.group() == ","
            and i + 1 < len(rows)
            and rows[i + 1].group() in [")", "]", "}"]
        )
    ]
    values = []
    for m in rows:
        value = m.group()
        if value.startswith(("'", '"')):
            try:
                value = "STRING:" + ast.literal_eval(value)
            except (SyntaxError, ValueError):
                pass
        values.append(value)
    return rows, values

changes = {}

def patch(name, old, new):
    text = changes.get(name, Path(name).read_text(encoding="utf-8"))
    spans, values = tokens(text)
    _, wanted = tokens(old)
    found = [
        i for i in range(len(values) - len(wanted) + 1)
        if values[i:i + len(wanted)] == wanted
    ]
    if len(found) != 1:
        raise SystemExit(
            f"版本不符：{name}（找到 {len(found)} 個位置）。"
            "尚未寫入任何檔案，請提供目前程式。"
        )
    i = found[0]
    changes[name] = (
        text[:spans[i].start()]
        + new
        + text[spans[i + len(wanted) - 1].end():]
    )

if Path("src/pending-renewals.ts").exists():
    raise SystemExit(
        "已存在待收款功能，請勿重複執行；如需修正請保留現有檔案。"
    )

patch('src/main.tsx', r'''
.event.type]}？
                  {modal.event.type.startsWith(
'''[1:-1], r'''
.event.type]}？
                  {modal.event.paymentConfirmation?"撤銷收款確認會恢復待收款，扣回當時計入的即時續約筆數；保留目前倉位租期，歷史 KPI 不變。":modal.event.type.startsWith(
'''[1:-1])

patch('src/main.tsx', r'''
note} />
                </label>
                <Submit busy={busy} /
'''[1:-1], r'''
note} />
                </label>
                {modal.code && modal.status === "rented" && <PendingEdit unit={modal}/>}
                <Submit busy={busy} /
'''[1:-1])

patch('src/main.tsx', r'''
=>
                                (status === "all" ||
                                  (status === "missing"
'''[1:-1], r'''
=>
                                (status === "all" || (status === "pendingRenewal" && pendingRenewals.some(p=>p.branchId===unit.branchId&&p.code===unit.code)) ||
                                  (status === "missing"
'''[1:-1])

patch('src/main.tsx', r'''
="missing">清單中消失</option>
                    </select>
'''[1:-1], r'''
="missing">清單中消失</option><option value="pendingRenewal">待收款續約</option>
                    </select>
'''[1:-1])

patch('src/main.tsx', r'''
== "units" && (
                <>
                  {branchId === "all" &&
'''[1:-1], r'''
== "units" && (
                <>
                  <PendingRenewals rows={pendingRenewals} busy={busy} onSave={run}/>
                  {branchId === "all" &&
'''[1:-1])

patch('src/main.tsx', r'''
branch.id === branchId),
  );
  const units: Row[]
'''[1:-1], r'''
branch.id === branchId),
  );
  const pendingRenewals=usePendingRenewals(visible,page==="units"&&(branchId!=="all"||loadAllUnits),setError);
  const units: Row[]
'''[1:-1])

patch('src/main.tsx', r'''
import InventoryReview from "./InventoryReview";
import TransferForm from
'''[1:-1], r'''
import {PendingEdit,PendingRenewals,usePendingRenewals} from "./PendingRenewals";
import InventoryReview from "./InventoryReview";
import TransferForm from
'''[1:-1])

patch('src/api.ts', r'''
{
      return removeImport(data);
    }
    case "reviewInventory": return reviewInventory(data)
'''[1:-1], r'''
{
      return removeImport(data);
    }
    case "confirmRenewalPayment": return confirmRenewalPayment(data);
    case "reviewInventory": return reviewInventory(data)
'''[1:-1])

patch('src/api.ts', r'''
{};
    }
    case "saveUnit": {
      const unit = normalizeUnits([
          { .
'''[1:-1], r'''
{};
    }
    case "saveUnit": {
      if(data.markRenewalPending && !data.remove)return savePendingUnit(data);
      const unit = normalizeUnits([
          { .
'''[1:-1])

patch('src/api.ts', r'''
data.eventId));
      if(["transferOut","transferIn"].includes(
'''[1:-1], r'''
data.eventId));
      if(check.data()?.paymentConfirmation)return undoRenewalPayment(data);
      if(["transferOut","transferIn"].includes(
'''[1:-1])

patch('src/api.ts', r'''
import {reviewInventory} from "./review-inventory";
import
'''[1:-1], r'''
import {savePendingUnit,confirmRenewalPayment,undoRenewalPayment} from "./pending-renewals";
import {reviewInventory} from "./review-inventory";
import
'''[1:-1])

patch('src/inventory-diff.js', r'''
new Error('異動類型與原倉位、新租期不一致');
 if(type==='renew'&&parseLease(before.leasePeriod|
'''[1:-1], r'''
new Error('異動類型與原倉位、新租期不一致');
 if(['renew','renewPending'].includes(type)&&parseLease(before.leasePeriod|
'''[1:-1])

patch(
    'src/inventory-diff.js',
    "|!rented))||(type==='renew'&&(!oldRented||!",
    "|!rented))||(['renew','renewPending'].includes(type)&&(!oldRented||!"
)

patch('src/inventory-diff.js', r'''
;
 if(!['new','renew','exit','transferIn','transferOut','sync'
'''[1:-1], r'''
;
 if(!['new','renew','renewPending','exit','transferIn','transferOut','sync'
'''[1:-1])

patch('src/inventory-diff.js', r'''
changed.includes('leasePeriod'))return 'renew';
 return 'sync';
}
export function validateInventoryChange
'''[1:-1], r'''
changed.includes('leasePeriod'))return 'renewPending';
 return 'sync';
}
export function validateInventoryChange
'''[1:-1])

patch('src/review-inventory.ts', r'''
;
    tx.set(unit,next);
    if(record){const
'''[1:-1], r'''
;
    tx.set(unit,next);
    if(job.type==='renewPending'&&!ps.exists())tx.set(pending,pendingRecord(next,job.date,uid,files.total));
    if(record){const
'''[1:-1])

patch('src/review-inventory.ts', r'''
leasePeriod?'rented':'vacant';const record=job.type!=='sync';
    const next:any={.
'''[1:-1], r'''
leasePeriod?'rented':'vacant';const record=!['sync','renewPending'].includes(job.type);
    const next:any={.
'''[1:-1])

patch(
    'src/review-inventory.ts',
    '),tx.get(nowMonth)]);\n    const b=bs.data',
    r'''
),tx.get(nowMonth),tx.get(pending)]);
    if(job.type==='renew'&&ps.exists())throw new Error(job.after.code+'：此租期已有收款追蹤紀錄，請改選待收款續約，並至倉位管理確認收款');
    const b=bs.data
'''[1:-1])

patch('src/review-inventory.ts', r'''
db,async tx=>{
    const [bs,us,ms,ns]=await Promise.all([
'''[1:-1], r'''
db,async tx=>{
    const pending=doc(branch,'pendingRenewals',renewalKey(job.after));
    const [bs,us,ms,ns,ps]=await Promise.all([
'''[1:-1])

patch(
    'src/review-inventory.ts',
    'import {collection,doc,getDoc,',
    r'''
import {pendingRecord,renewalKey} from "./pending-renewals";
import {collection,doc,getDoc,
'''[1:-1])

patch(
    'src/InventoryReview.tsx',
    ".status==='rented'?['renew','exit','transferOut','sync']",
    ".status==='rented'?['renewPending','renew','exit','transferOut','sync']"
)

patch('src/InventoryReview.tsx', r'''
倉位預設盤點；已有倉位的租期、狀態變更會預設對應異動。</p>
   <label className
'''[1:-1], r'''
倉位預設盤點；已出租倉位更換租期預設待收款續約，只更新租期；確認收款後才計入續約。</p>
   <label className
'''[1:-1])

patch(
    'src/InventoryReview.tsx',
    "'資料修正／盤點（不計異動）',new:'承租',renew:'續約',exit:'退租',transferIn:'轉入'",
    "'資料修正／盤點（不計異動）',new:'承租',renew:'已收款續約',renewPending:'待收款續約（不計續約）',exit:'退租',transferIn:'轉入'"
)

patch('firestore.rules', r'''
data.voidedAt == request.time));
    allow delete: if false
'''[1:-1], r'''
data.voidedAt == request.time)));
    allow delete: if false
'''[1:-1])

patch('firestore.rules', r'''
==eventId;
    allow update: if transferUndoValid() && (((
'''[1:-1], r'''
==eventId;
    allow update: if !resource.data.get('paymentConfirmation',false) && (transferUndoValid() && (((
'''[1:-1])

patch('firestore.rules', r'''
= request.auth.uid;
    }
    allow read: if branchAccess(id);
    allow create: if branchEdit(id) && (unlocked(id)
'''[1:-1], r'''
= request.auth.uid;
    }
    function paymentCreate() {
     let e=request.resource.data;
     let path=/databases/$(database)/documents/branches/$(id)/pendingRenewals/$(e.pendingId);
     let before=get(path).data;let after=getAfter(path).data;
     return e.keys().hasOnly(['code','type','date','month','activities','unitSnapshot','priceSnapshot','previousLease','previousEventId','previousEventDate','paymentConfirmation','pendingId','kpiCounted','createdBy','createdAt','voided'])
      && e.paymentConfirmation && e.type=='renew' && !e.voided && e.activities==[]
      && e.createdBy==request.auth.uid && e.createdAt==request.time
      && e.date.matches('[0-9]{4}-[0-9]{2}-[0-9]{2}') && e.month.matches('[0-9]{4}-(0[1-9]|1[0-2])')
      && e.code==before.code && e.unitSnapshot==before.unitSnapshot
      && before.status=='pending' && after.status=='paid' && after.eventId==eventId
      && after.paymentMonth==e.month && after.paymentDate==e.date
      && e.kpiCounted==(getAfter(/databases/$(database)/documents/branches/$(id)/months/$(e.month)).data.get('source','live')!='import') && renewalDelta(e.month,1,e.kpiCounted);
    }
    function paymentVoid() {
     let old=resource.data;let e=request.resource.data;
     let p=getAfter(/databases/$(database)/documents/branches/$(id)/pendingRenewals/$(old.get('pendingId',e.get('pendingId','')))).data;
     return old.type=='renew' && !old.voided && e.voided && e.voidMode=='paymentPending'
      && e.diff(old).affectedKeys().hasOnly(['voided','voidMode','voidedBy','voidedAt','pendingId'])
      && e.voidedBy==request.auth.uid && e.voidedAt==request.time
      && p.status=='pending' && p.code==old.code && p.leasePeriod==old.unitSnapshot.leasePeriod
      && (old.get('paymentConfirmation',false) ? p.eventId==null : p.reclassifiedEventId==eventId && p.createdAt==request.time && p.createdBy==request.auth.uid)
      && renewalDelta(old.month,-1,old.get('kpiCounted',true));
    }
    allow read: if branchAccess(id);
    allow create: if branchEdit(id) && unlocked(id) && paymentCreate();
    allow update: if branchEdit(id) && unlocked(id) && paymentVoid();
    allow create: if branchEdit(id) && !request.resource.data.get('paymentConfirmation',false) && (unlocked(id)
'''[1:-1])

patch('firestore.rules', r'''
data.status=='vacant';
   }
   match /events/{eventId} {
'''[1:-1], r'''
data.status=='vacant';
   }
   // storeasy-pending-renewals-v1
   function renewalDelta(month,delta,counted) {
    let path=/databases/$(database)/documents/branches/$(id)/months/$(month);
    let before=exists(path)?get(path).data:{};
    let after=existsAfter(path)?getAfter(path).data:{};
    return before.get('source','live')=='import' || !counted
     ? after==before : after.get('renew',0)==before.get('renew',0)+delta;
   }
   match /pendingRenewals/{pendingId} {
    function validPending(d) {
     return d.keys().hasOnly(['code','leasePeriod','leaseStart','leaseEnd','status','observedDate','source','createdBy','createdAt','updatedBy','updatedAt','eventId','paymentMonth','paymentDate','unitSnapshot','reclassifiedEventId'])
      && d.code is string && d.leasePeriod is string && d.leasePeriod.size()>0
      && d.leaseStart is string && d.leaseEnd is string && pendingId==d.code+'_'+d.leaseStart+'_'+d.leaseEnd
      && d.unitSnapshot.leasePeriod==d.leasePeriod && d.unitSnapshot.leaseStart==d.leaseStart && d.unitSnapshot.leaseEnd==d.leaseEnd
      && d.status in ['pending','paid'] && d.updatedBy==request.auth.uid && d.updatedAt==request.time;
    }
    function pairedPayment() {
     let d=request.resource.data;
     let e=getAfter(/databases/$(database)/documents/branches/$(id)/events/$(d.eventId)).data;
     return e.paymentConfirmation && !e.voided && e.pendingId==pendingId && e.code==d.code
      && e.unitSnapshot==d.unitSnapshot && e.createdBy==request.auth.uid && e.createdAt==request.time
      && e.month==d.paymentMonth && e.date==d.paymentDate && e.kpiCounted==(getAfter(/databases/$(database)/documents/branches/$(id)/months/$(e.month)).data.get('source','live')!='import') && renewalDelta(e.month,1,e.kpiCounted);
    }
    function pairedUndo() {
     let e=getAfter(/databases/$(database)/documents/branches/$(id)/events/$(resource.data.eventId)).data;
     return e.voided && e.voidMode=='paymentPending' && e.voidedBy==request.auth.uid && e.voidedAt==request.time
      && renewalDelta(e.month,-1,e.kpiCounted);
    }
    allow read: if branchAccess(id);
    allow create: if branchEdit(id) && (unlocked(id)||ownImport(id)) && validPending(request.resource.data)
     && request.resource.data.status=='pending' && request.resource.data.eventId==null
     && request.resource.data.paymentDate==null && request.resource.data.paymentMonth==null
     && request.resource.data.createdBy==request.auth.uid && request.resource.data.createdAt==request.time
     && getAfter(/databases/$(database)/documents/branches/$(id)/units/$(request.resource.data.code)).data.leasePeriod==request.resource.data.leasePeriod;
    allow update: if branchEdit(id) && unlocked(id) && validPending(request.resource.data)
     && request.resource.data.diff(resource.data).affectedKeys().hasOnly(['status','eventId','paymentMonth','paymentDate','updatedBy','updatedAt'])
     && (resource.data.status=='pending' && request.resource.data.status=='paid' && pairedPayment()
      || resource.data.status=='paid' && request.resource.data.status=='pending'
       && request.resource.data.eventId==null && request.resource.data.paymentMonth==null && request.resource.data.paymentDate==null && pairedUndo());
    allow delete: if false;
   }
   match /events/{eventId} {
'''[1:-1])

changes['src/pending-renewals.ts'] = r'''
import {collection,doc,getDoc,getDocs,query,where,runTransaction,serverTimestamp} from 'firebase/firestore';
import {auth,db} from './firebase';
import {normalizeUnits,taipeiDate,validDate} from './domain.js';
import {parseLease} from './lease.js';
import {pricingUpdate} from './pricing.js';

export const renewalKey=(u:any)=>`${u.code}_${u.leaseStart}_${u.leaseEnd}`;

export function pendingRecord(unit:any,date:string,uid:string,source=''){
 return {
  code:unit.code,
  leasePeriod:unit.leasePeriod,
  leaseStart:unit.leaseStart,
  leaseEnd:unit.leaseEnd,
  status:'pending',
  observedDate:date,
  source,
  createdBy:uid,
  createdAt:serverTimestamp(),
  updatedBy:uid,
  updatedAt:serverTimestamp(),
  eventId:null,
  paymentMonth:null,
  paymentDate:null,
  unitSnapshot:{
   dimensions:unit.dimensions,
   volume:unit.volume,
   price:unit.price,
   note:unit.note,
   leasePeriod:unit.leasePeriod,
   leaseStart:unit.leaseStart,
   leaseEnd:unit.leaseEnd
  }
 };
}

function signed(){
 const uid=auth.currentUser?.uid;
 if(!uid)throw new Error('請先登入');
 return uid;
}

export async function matchingRenewals(branchId:string,code:string,period:string){
 const normalized=parseLease(period).leasePeriod;
 const rows=await getDocs(query(
  collection(db,'branches',branchId,'events'),
  where('code','==',code)
 ));
 return rows.docs.filter(d=>{
  const e=d.data();
  return e.type==='renew'&&!e.voided
   &&parseLease(e.unitSnapshot?.leasePeriod||'').leasePeriod===normalized;
 }).map(d=>({id:d.id,...d.data()} as any));
}

export async function savePendingUnit(data:any){
 const uid=signed();
 const unit=normalizeUnits([{...data,price:Number(data.price||0)}])[0];
 const date=taipeiDate();
 if(!unit.leasePeriod)throw new Error('待收款續約必須填寫租期');

 const b=doc(db,'branches',data.branchId);
 const u=doc(b,'units',unit.code);
 const p=doc(b,'pendingRenewals',renewalKey(unit));
 const matches=await matchingRenewals(data.branchId,unit.code,unit.leasePeriod);

 if(matches.length>1&&!data.pendingEventId)
  throw new Error('此租期有多筆續約紀錄，請在待收款選項中選擇要更正的那一筆');

 const match=matches.find(e=>e.id===data.pendingEventId)
  ||(matches.length===1?matches[0]:null);

 if(data.pendingEventId&&!match)
  throw new Error('所選續約紀錄已變更，請重新開啟編輯');

 await runTransaction(db,async t=>{
  const [bs,us,ps]=await Promise.all([t.get(b),t.get(u),t.get(p)]);

  if(!bs.exists()||bs.data().importing||us.data()?.status!=='rented')
   throw new Error('倉位已變更或據點正在匯入，請重新開啟編輯');

  const existing=ps.data();
  if(existing?.status==='paid')
   throw new Error('此租期已確認收款，請先在異動紀錄撤銷該次收款確認');

  const e=match?doc(b,'events',match.id):null;
  const es=e?await t.get(e):null;
  const event=es?.data();
  const m=event?doc(b,'months',event.month):null;
  const ms=m?await t.get(m):null;

  if(event&&(
   event.voided||event.type!=='renew'||event.code!==unit.code
   ||parseLease(event.unitSnapshot?.leasePeriod||'').leasePeriod!==unit.leasePeriod
  ))throw new Error('續約紀錄已變更，請重新開啟編輯');

  const next={
   ...us.data(),...unit,
   ...pricingUpdate(us.data(),unit,date,bs.data().inventoryDate)
  };

  t.set(u,{...next,updatedAt:serverTimestamp()});

  if(!existing)t.set(p,{
   ...pendingRecord(next,date,uid,'編輯標記'),
   reclassifiedEventId:match?.id||null
  });

  if(event&&e){
   t.update(e,{
    voided:true,
    voidMode:'paymentPending',
    voidedBy:uid,
    voidedAt:serverTimestamp(),
    pendingId:p.id
   });
   if(ms?.data()?.source!=='import'&&event.kpiCounted!==false){
    if(!(ms?.data()?.renew>0))
     throw new Error('原月份續約數不一致，無法自動更正，請先核對');
    t.set(m!,{
     renew:ms!.data()!.renew-1,
     updatedAt:serverTimestamp()
    },{merge:true});
   }
  }

  t.update(b,{
   revision:bs.data().revision+1,
   updatedAt:serverTimestamp()
  });
 });
 return {};
}

export async function confirmRenewalPayment(data:any){
 const uid=signed();
 const date=data.date||taipeiDate();
 const month=String(data.month||'');

 if(!validDate(date)||date>taipeiDate()
  ||!/^20\d{2}-(0[1-9]|1[0-2])$/.test(month))
  throw new Error('請填寫正確的收款日期及統計月份');

 const b=doc(db,'branches',data.branchId);
 const p=doc(b,'pendingRenewals',data.pendingId);
 const m=doc(b,'months',month);
 const e=doc(collection(b,'events'));

 await runTransaction(db,async t=>{
  const [bs,ps,ms]=await Promise.all([t.get(b),t.get(p),t.get(m)]);
  if(!bs.exists()||bs.data().importing)
   throw new Error('據點正在匯入，請稍後再試');

  const r=ps.data();
  if(!r)throw new Error('待收款紀錄不存在');
  if(r.status==='paid')return;

  const counted=ms.data()?.source!=='import';

  t.set(e,{
   code:r.code,type:'renew',date,month,activities:[],
   unitSnapshot:r.unitSnapshot,
   priceSnapshot:{price:r.unitSnapshot.price},
   previousLease:{
    leasePeriod:r.leasePeriod,
    leaseStart:r.leaseStart,
    leaseEnd:r.leaseEnd
   },
   previousEventId:null,
   previousEventDate:null,
   paymentConfirmation:true,
   pendingId:p.id,
   kpiCounted:counted,
   createdBy:uid,
   createdAt:serverTimestamp(),
   voided:false
  });

  t.update(p,{
   status:'paid',
   eventId:e.id,
   paymentMonth:month,
   paymentDate:date,
   updatedBy:uid,
   updatedAt:serverTimestamp()
  });

  if(counted)t.set(m,{
   source:'live',
   renew:(ms.data()?.renew||0)+1,
   updatedAt:serverTimestamp()
  },{merge:true});

  t.update(b,{
   revision:bs.data().revision+1,
   updatedAt:serverTimestamp()
  });
 }).catch(async error=>{
  if(error.code==='permission-denied'
   &&(await getDoc(p)).data()?.status==='paid')return;
  throw error;
 });
 return {};
}

export async function undoRenewalPayment(data:any){
 const uid=signed();
 const b=doc(db,'branches',data.branchId);
 const e=doc(b,'events',data.eventId);

 await runTransaction(db,async t=>{
  const [bs,es]=await Promise.all([t.get(b),t.get(e)]);
  const event=es.data();

  if(!bs.exists()||bs.data().importing
   ||!event?.paymentConfirmation||event.voided)
   throw new Error('收款紀錄已變更或據點正在匯入');

  const p=doc(b,'pendingRenewals',event.pendingId);
  const m=doc(b,'months',event.month);
  const [ps,ms]=await Promise.all([t.get(p),t.get(m)]);

  if(ps.data()?.eventId!==e.id||ps.data()?.status!=='paid')
   throw new Error('待收款紀錄已變更');

  if(ms.data()?.source!=='import'&&event.kpiCounted){
   if(!(ms.data()?.renew>0))
    throw new Error('續約數不一致，請先核對');
   t.set(m,{
    renew:ms.data()!.renew-1,
    updatedAt:serverTimestamp()
   },{merge:true});
  }

  t.update(e,{
   voided:true,
   voidMode:'paymentPending',
   voidedBy:uid,
   voidedAt:serverTimestamp()
  });
  t.update(p,{
   status:'pending',
   eventId:null,
   paymentMonth:null,
   paymentDate:null,
   updatedBy:uid,
   updatedAt:serverTimestamp()
  });
  t.update(b,{
   revision:bs.data().revision+1,
   updatedAt:serverTimestamp()
  });
 });
 return {};
}
'''[1:-1]

changes['src/PendingRenewals.tsx'] = r'''
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
'''[1:-1]

for name, content in changes.items():
    path = Path(name)
    if path.exists():
        backup = path.with_name(path.name + ".before-pending")
        if not backup.exists():
            backup.write_text(
                path.read_text(encoding="utf-8"),
                encoding="utf-8"
            )
    path.write_text(content, encoding="utf-8")

print("更新完成。請執行 npm run build，並發布更新後的 firestore.rules。")
