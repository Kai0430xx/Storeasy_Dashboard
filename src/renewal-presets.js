import {validDate,taipeiDate} from './domain.js';
import {parseLease} from './lease.js';
export function renewalStart(unit){
 let end=unit?.leaseEnd;
 try{end=parseLease(unit?.leasePeriod||'').leaseEnd||end;}catch{}
 return validDate(end)?new Date(Date.parse(end+'T00:00:00Z')+86400000).toISOString().slice(0,10):taipeiDate();
}
export function renewalPeriod(start,months){
 if(!validDate(start)||start<'2000-01-01'||start>'2099-12-31'||![1,3,6,12].includes(months))throw Error('請選擇有效開始日期與租期。');
 const [year,month,day]=start.split('-').map(Number);
 const target=new Date(Date.UTC(year,month-1+months,1));
 const last=new Date(Date.UTC(target.getUTCFullYear(),target.getUTCMonth()+1,0)).getUTCDate();
 const end=new Date(Date.UTC(target.getUTCFullYear(),target.getUTCMonth(),Math.min(day,last))-86400000);
 const finish=end.toISOString().slice(0,10);
 if(finish>'2099-12-31')throw Error('租期不得超過2099年。');
 return `${start.replace(/-/g,'/')}－${finish.replace(/-/g,'/')}`;
}
