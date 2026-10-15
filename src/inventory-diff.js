import {normalizeUnits} from './domain.js';
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
 if(row.before.status==='rented'&&row.after.status==='rented'&&row.changed.includes('leasePeriod'))return 'renewPending';
 return 'sync';
}
export function validateInventoryChange(before,after,change,today){
 const type=change.type;
 if(!['new','renew','renewPending','exit','transferIn','transferOut','sync'].includes(type))
  throw new Error('請選擇異動類型');
 if(!inventoryMonths(today).includes(change.month))
  throw new Error('請選擇上個月、本月或下個月');
 const oldRented=before?.status==='rented',rented=Boolean(after.leasePeriod);
 if(
  (['new','transferIn'].includes(type)&&(oldRented||!rented))||(['renew','renewPending'].includes(type)&&(!oldRented||!rented))
  ||(['exit','transferOut'].includes(type)&&(!oldRented||rented))
 )throw new Error('異動類型與原倉位、新租期不一致');
 if(['renew','renewPending'].includes(type)&&parseLease(before.leasePeriod||'').leasePeriod===after.leasePeriod)
  throw new Error('續約的新租期必須與原租期不同');
 if(type==='exit'&&(
  !['價格','距離','不再需要','改租其它倉位/據點','服務或環境','其它'].includes(change.exitCategory)
  ||!String(change.exitReason||'').trim()
  ||String(change.exitReason).trim().length>500
 ))throw new Error('退租請選原因分類，並填寫1～500字的原因');
}

// storeasy-inventory-review-v1
