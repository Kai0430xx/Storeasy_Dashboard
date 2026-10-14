import {rentalDetails} from './lease-term.js';
export const renewTermKeys=['monthly','quarterly','halfYear','yearly'];
export function validateRenewCounts(value,total) {
 if(value==null)return null;
 if(typeof value!=='object'||Array.isArray(value)||Object.keys(value).length!==4||Object.keys(value).some(k=>!renewTermKeys.includes(k)))throw Error('KPI 續約租期分項不合法');
 const counts=Object.fromEntries(renewTermKeys.map(k=>{
  const n=value[k];if(n!==null&&(!Number.isInteger(n)||n<0))throw Error('KPI 續約租期分項不合法');
  return [k,n];
 }));
 if(total!=null&&renewTermKeys.every(k=>counts[k]!=null)&&renewTermKeys.reduce((n,k)=>n+counts[k],0)!==total)throw Error('KPI 續約分項與總筆數不符');
 return counts;
}
export function rentalSummary(events,units,type,month,kpiMonths=[]) {
 const imported=type==='renew'?kpiMonths.filter(m=>m.source==='import'&&(m.month||m.id)===month):[];
 const ids=new Set(imported.map(m=>m.branchId));
 const result=rentalDetails(events.filter(e=>!ids.has(e.branchId)),units,type,month);
 let missingKpi=false;
 for(const m of imported){
  const split=validateRenewCounts(m.renewByTerm,m.renew);
  if(!split){missingKpi=true;for(const k of renewTermKeys)result.counts[k]=null;result.counts.unknown+=m.renew||0;continue;}
  for(const k of renewTermKeys){if(split[k]==null){missingKpi=true;result.counts[k]=null;}else if(result.counts[k]!=null)result.counts[k]+=split[k];}
 }
 return {...result,missingKpi};
}
