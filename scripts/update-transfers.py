from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MARK = 'storeasy-transfers-v1'
prepared = {}


def sub(s, pattern, value):
    s, n = re.subn(
        pattern,
        lambda m: value(m) if callable(value) else value,
        s
    )
    if n != 1:
        raise RuntimeError('版本不符，未寫入：' + pattern[:80])
    return s


p = ROOT / 'src/main.tsx'
s = p.read_text(encoding='utf-8')
if MARK not in s:
    s = 'import TransferForm from "./TransferForm";\n' + s
    s = sub(
        s,
        r'const types: Row = \{[\s\S]*?\};',
        'const types: Row = { new:"新承租",renew:"續約",exit:"退租",transferOut:"轉出",transferIn:"轉入" };'
    )

    def buttons(m):
        u = m.group(1)
        return (
            "{!" + u + ".missing && (" + u
            + ".status==='rented'?['renew','exit','transferOut']:['new','transferIn']).map(type=><button className=\"text-button\" key={type} onClick={()=>{setMonth(today().slice(0,7));setModal({kind:type.startsWith('transfer')?'transfer':'event',unit:"
            + u
            + ",type});}}>{type==='new'?'承租':types[type]}</button>)}"
        )

    s = sub(
        s,
        r'\{!([A-Za-z]\w*)\.missing && \([\s\S]*?</>\s*\)\}',
        buttons
    )
    s = sub(
        s,
        r'event: `登記\$\{types\[modal.type\]\}`,',
        'event: `登記${types[modal.type]}`,transfer: `登記${types[modal.type]}`,'
    )
    s = sub(
        s,
        r'\{modal.kind === "event" && \(',
        '{modal.kind === "transfer" && <TransferForm unit={modal.unit} type={modal.type} units={units} busy={busy} onDateChange={setMonth} onSave={(data:Row)=>run(()=>call("recordTransfer",data),"轉倉已儲存，不計入新承租或退租")} />}\n            {modal.kind === "event" && ('
    )
    s = sub(
        s,
        r'call\("voidEvent",',
        'call(modal.event.type.startsWith("transfer")?"undoTransfer":"voidEvent",'
    )
    a = s.index('{modal.kind === "void"')
    b = s.index('{modal.kind === "deleteUnit"', a)
    segment = s[a:b]
    segment = sub(
        segment,
        r'\{profile\?\.role === "admin"',
        '{modal.event.type.startsWith("transfer")?"轉倉只能撤銷最後一筆；同店轉倉會一併還原原倉與目的倉，兩間都不能有後續異動。":profile?.role === "admin"'
    )
    s = s[:a] + segment + s[b:]
    prepared['src/main.tsx'] = s


p = ROOT / 'src/api.ts'
s = p.read_text(encoding='utf-8')
if MARK not in s:
    s = 'import {recordTransfer,undoTransfer} from "./transfers";\n' + s
    if not re.search(r'\bgetDoc\s*,', s):
        s = sub(s, r'\bgetDocs\s*,', 'getDoc, getDocs,')
    s = sub(
        s,
        r'case "recordEvent": \{',
        'case "recordTransfer": return recordTransfer(data);\n    case "undoTransfer": return undoTransfer(data);\n    case "recordEvent": {'
    )
    s = sub(
        s,
        r'case "voidEvent": \{',
        'case "voidEvent": {\n      const check=await getDoc(doc(db,"branches",data.branchId,"events",data.eventId));\n      if(["transferOut","transferIn"].includes(check.data()?.type))return undoTransfer(data);'
    )
    prepared['src/api.ts'] = s


RULE_HELPERS = r"""    function transferValid() {
     let e=request.resource.data;
     let before=get(/databases/$(database)/documents/branches/$(id)/units/$(e.code)).data;
     let after=getAfter(/databases/$(database)/documents/branches/$(id)/units/$(e.code)).data;
     return !(e.type in ['transferOut','transferIn']) || (
      e.activities==[] && e.transferMode in ['local','external'] && e.transferGroup is string
      && ((e.type=='transferOut' && before.status=='rented' && after.status=='vacant' && after.leasePeriod=='')
       || (e.type=='transferIn' && before.status=='vacant' && after.status=='rented' && after.leasePeriod is string && after.leasePeriod.size()>0))
      && (e.transferMode=='external' ? e.peerCode=='' && e.peerEventId=='' : pairedTransfer(e))
     );
    }
    function pairedTransfer(e) {
     let peer=getAfter(/databases/$(database)/documents/branches/$(id)/events/$(e.peerEventId)).data;
     return e.peerCode!=e.code && peer.code==e.peerCode && peer.peerCode==e.code && peer.peerEventId==eventId
      && peer.transferGroup==e.transferGroup && peer.transferMode=='local' && peer.date==e.date && peer.month==e.month
      && peer.createdBy==request.auth.uid && peer.createdAt==request.time && !peer.voided
      && peer.type==(e.type=='transferOut'?'transferIn':'transferOut');
    }
    function transferUndoValid() {
     let e=resource.data;
     return !(e.type in ['transferOut','transferIn']) || (request.resource.data.get('voidMode','rollback')=='rollback'
      && (e.transferMode=='external' || (getAfter(/databases/$(database)/documents/branches/$(id)/events/$(e.peerEventId)).data.voided
       && getAfter(/databases/$(database)/documents/branches/$(id)/events/$(e.peerEventId)).data.voidedAt==request.time)));
    }

"""

p = ROOT / 'firestore.rules'
s = p.read_text(encoding='utf-8')
if MARK not in s:
    s = re.sub(
        r"e.type\s*==\s*'new'(?=\s*&&\s*(?:resource|request\.resource)\.data\.status)",
        "e.type in ['new','transferIn']",
        s
    )
    s = re.sub(
        r"e.type\s*==\s*'exit'(?=\s*&&\s*(?:resource|request\.resource)\.data\.status)",
        "e.type in ['exit','transferOut']",
        s
    )
    a = s.index('match /events/{eventId}')
    b = s.index('match /activities/{activityId}', a)
    segment = s[a:b]
    segment = sub(
        segment,
        r'match /events/\{eventId\} \{',
        'match /events/{eventId} {\n' + RULE_HELPERS
    )
    segment = sub(
        segment,
        r"request.resource.data.type\s+in\s+\[\s*'new',\s*'renew',\s*'exit'\s*\]",
        "transferValid() && request.resource.data.type in ['new','renew','exit','transferOut','transferIn']"
    )
    segment = sub(
        segment,
        r'allow update: if ([\s\S]*?);',
        lambda m: 'allow update: if transferUndoValid() && (' + m.group(1) + ');'
    )
    s = s[:a] + segment + s[b:]
    prepared['firestore.rules'] = s


TEXT = r"""import {collection,doc,getDoc,runTransaction,serverTimestamp} from 'firebase/firestore';
import {auth,db} from './firebase';
import {parseLease} from './lease.js';
import {validDate,taipeiDate} from './domain.js';
import {priceSnapshot} from './pricing.js';

const time=()=>serverTimestamp();
const key=(v:any)=>{
 if(typeof v!=='string'||!v||v.includes('/'))throw new Error('據點或倉位編號不合法');
 return v;
};
const previous=(u:any)=>({
 leasePeriod:u.leasePeriod||'',
 leaseStart:u.leaseStart||null,
 leaseEnd:u.leaseEnd||null,
 vacantSince:u.vacantSince||null
});

export async function recordTransfer(data:any){
 const branchId=key(data.branchId),code=key(data.code),date=data.date,uid=auth.currentUser?.uid;
 if(!uid)throw new Error('請先登入');
 if(!['transferOut','transferIn'].includes(data.type)||!validDate(date)||date>taipeiDate())throw new Error('轉倉日期或類型不合法');
 const local=data.type==='transferOut'&&data.mode==='local';
 if(data.type==='transferOut'&&!['local','external'].includes(data.mode))throw new Error('請選擇轉出方式');
 const target=local?key(data.targetCode):null;
 if(target===code)throw new Error('不能轉到原倉位');
 const lease=data.type==='transferIn'||local?parseLease(data.leasePeriod):null;
 if(lease&&!lease.leasePeriod)throw new Error('請填寫新租期');

 const branch=doc(db,'branches',branchId);
 const month=doc(branch,'months',date.slice(0,7));
 const nowMonth=doc(branch,'months',taipeiDate().slice(0,7));
 const refs=[doc(branch,'units',code),...(local?[doc(branch,'units',target!)]:[])];
 const eventRefs=refs.map(()=>doc(collection(branch,'events')));
 const group=eventRefs[0].id;

 await runTransaction(db,async tx=>{
  const [bs,ms,ns,...units]=await Promise.all([
   tx.get(branch),tx.get(month),tx.get(nowMonth),...refs.map(r=>tx.get(r))
  ]);
  if(!bs.exists()||units.some(u=>!u.exists()))throw new Error('據點或倉位不存在');
  const b=bs.data();
  if(b.importing)throw new Error('據點正在匯入');
  if(ms.data()?.source==='import')throw new Error('該月已匯入歷史 KPI，不能新增異動');

  const rows=units.map(u=>u.data()!);
  rows.forEach((u,i)=>{
   const expected=i===0&&data.type==='transferOut'?'rented':'vacant';
   if(u.archived||u.missing||u.status!==expected||Boolean(u.leasePeriod)!==(expected==='rented'))throw new Error('倉位狀態已變更，請重新選擇');
   if(u.lastEventDate&&date<u.lastEventDate)throw new Error('日期不得早於倉位上一筆異動');
  });

  const delta=local?0:data.type==='transferIn'?1:-1;
  const rented=b.rented+delta,vacant=b.vacant-delta;
  if(rented<0||vacant<0)throw new Error('倉位統計不一致');

  rows.forEach((u,i)=>{
   const type=i===0?data.type:'transferIn';
   const out=type==='transferOut';
   const newLease=out?parseLease(''):lease!;
   tx.update(refs[i],{
    ...newLease,
    status:out?'vacant':'rented',
    vacantSince:out?date:null,
    lastEventDate:date,
    lastEventId:eventRefs[i].id,
    updatedAt:time()
   });
   const price=priceSnapshot(u,date);
   tx.set(eventRefs[i],{
    code:refs[i].id,type,date,month:date.slice(0,7),
    activities:[],exitReason:'',exitCategory:'',
    transferGroup:group,
    transferMode:local?'local':'external',
    peerCode:local?refs[1-i].id:'',
    peerEventId:local?eventRefs[1-i].id:'',
    priceSnapshot:price,
    unitSnapshot:{
     dimensions:u.dimensions,volume:u.volume,
     price:price.price,note:u.note,...newLease
    },
    previousLease:previous(u),
    previousEventDate:u.lastEventDate||null,
    previousEventId:u.lastEventId||null,
    createdBy:uid,createdAt:time(),voided:false
   });
  });

  tx.update(branch,{rented,vacant,revision:b.revision+1,updatedAt:time()});
  tx.set(month,{
   source:'live',
   ...(data.type==='transferOut'?{transferOut:(ms.data()?.transferOut||0)+1}:{}),
   ...(data.type==='transferIn'||local?{transferIn:(ms.data()?.transferIn||0)+1}:{}),
   ...(date.slice(0,7)===taipeiDate().slice(0,7)?{
    total:b.total,rented,vacant,snapshotDate:taipeiDate()
   }:{}),
   updatedAt:time()
  },{merge:true});
  if(month.id!==nowMonth.id&&ns.data()?.source!=='import'){
   tx.set(nowMonth,{
    source:'live',total:b.total,rented,vacant,
    snapshotDate:taipeiDate(),updatedAt:time()
   },{merge:true});
  }
 });
}

export async function undoTransfer(data:any){
 const branch=doc(db,'branches',key(data.branchId));
 const eventRef=doc(branch,'events',key(data.eventId));
 const uid=auth.currentUser?.uid;
 if(!uid)throw new Error('請先登入');

 await runTransaction(db,async tx=>{
  const first=await tx.get(eventRef);
  if(!first.exists())throw new Error('轉倉紀錄不存在');
  const e=first.data();
  const events=[{ref:eventRef,data:e}];
  if(e.transferMode==='local'){
   const peerRef=doc(branch,'events',key(e.peerEventId));
   const peer=await tx.get(peerRef);
   if(!peer.exists()||peer.data().transferGroup!==e.transferGroup)throw new Error('配對的轉倉紀錄不一致');
   events.push({ref:peerRef,data:peer.data()});
  }
  const month=doc(branch,'months',e.month);
  const nowMonth=doc(branch,'months',taipeiDate().slice(0,7));
  const units=events.map(x=>doc(branch,'units',x.data.code));
  const [bs,ms,ns,...us]=await Promise.all([
   tx.get(branch),tx.get(month),tx.get(nowMonth),...units.map(r=>tx.get(r))
  ]);
  if(!bs.exists()||bs.data().importing||ms.data()?.source!=='live')throw new Error('據點正在匯入或此月份不能撤銷');

  let delta=0;
  const counts:any={};
  events.forEach((x,i)=>{
   const u=us[i].data(),out=x.data.type==='transferOut';
   if(!['transferOut','transferIn'].includes(x.data.type)||x.data.voided||!u||u.archived||u.missing||u.lastEventId!==x.ref.id||u.status!==(out?'vacant':'rented'))throw new Error('轉倉後已有其它異動，不能撤銷；同店轉倉須兩間倉位皆為最後一筆異動');
   if(!Number.isInteger(ms.data()?.[x.data.type])||ms.data()![x.data.type]<1)throw new Error('轉倉統計不一致');
   delta+=out?1:-1;
   counts[x.data.type]=ms.data()![x.data.type]-1;
  });

  const b=bs.data(),rented=b.rented+delta,vacant=b.vacant-delta;
  if(rented<0||vacant<0)throw new Error('倉位統計不一致');
  events.forEach((x,i)=>{
   const out=x.data.type==='transferOut';
   tx.update(units[i],{
    ...x.data.previousLease,
    status:out?'rented':'vacant',
    lastEventId:x.data.previousEventId,
    lastEventDate:x.data.previousEventDate,
    updatedAt:time()
   });
   tx.update(x.ref,{
    voided:true,voidedBy:uid,voidedAt:time(),voidMode:'rollback'
   });
  });
  tx.update(branch,{rented,vacant,revision:b.revision+1,updatedAt:time()});
  tx.set(month,{
   ...counts,
   ...(month.id===nowMonth.id?{
    total:b.total,rented,vacant,snapshotDate:taipeiDate()
   }:{}),
   updatedAt:time()
  },{merge:true});
  if(month.id!==nowMonth.id&&ns.data()?.source!=='import'){
   tx.set(nowMonth,{
    source:'live',total:b.total,rented,vacant,
    snapshotDate:taipeiDate(),updatedAt:time()
   },{merge:true});
  }
 });
}
"""
name = 'src/transfers.ts'
p = ROOT / name
if p.exists() and MARK not in p.read_text(encoding='utf-8'):
    raise RuntimeError(name + ' 已有不同版本，未寫入任何檔案')
if not p.exists():
    prepared[name] = TEXT


TEXT = r"""import React,{useState} from 'react';
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
"""
name = 'src/TransferForm.tsx'
p = ROOT / name
if p.exists() and MARK not in p.read_text(encoding='utf-8'):
    raise RuntimeError(name + ' 已有不同版本，未寫入任何檔案')
if not p.exists():
    prepared[name] = TEXT


for name, text in prepared.items():
    (ROOT / name).write_text(
        text + '\n// ' + MARK + '\n',
        encoding='utf-8'
    )
    print('已更新 ' + name)

print('完成。請將 GitHub 最新 firestore.rules 全文發布至 Firebase。')
