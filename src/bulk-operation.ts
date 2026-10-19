
import {inventorySignature} from './inventory-diff.js';

export function bulkFingerprint(data:any){
 if(!data.operationId)return null;
 if(!/^bulk_[a-zA-Z0-9-]{16,80}$/.test(data.operationId)||typeof data.expectedUnit!=='string'){
  throw Error('批次資料不完整，請重新選取倉位');
 }
 return JSON.stringify([
  data.branchId,data.code,data.type,data.date,data.leasePeriod||'',
  data.unpaid==='on',[...new Set(data.activityIds||[])].sort(),
  String(data.exitCategory||''),String(data.exitReason||'').trim(),
  data.expectedUnit
 ]);
}

export function checkBulkUnit(data:any,unit:any){
 if(data.operationId&&inventorySignature(unit)!==data.expectedUnit){
  throw Error('倉位在選取後已被修改，請重新核對並建立新批次');
 }
}
