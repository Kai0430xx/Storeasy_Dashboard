import {operatingMonths} from './operating-months.js';
export function referralMonths(year,today,referrals,branch={}) {
  const {startMonth}=operatingMonths(year,branch);
  return new Set(referrals.filter(r=>{
    const month=r.month||r.id||'';
    return new RegExp(`^${year}-(0[1-9]|1[0-2])$`).test(month)
      && Number(month.slice(5,7))>=startMonth && month<=today.slice(0,7)
      && Number.isFinite(r.count) && r.count>=3;
  }).map(r=>r.month||r.id)).size;
}
