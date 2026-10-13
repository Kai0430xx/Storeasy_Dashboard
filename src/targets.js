import { validDate } from './domain.js';
export const exitCategories = ['價格','距離','不再需要','改租其它倉位/據點','服務或環境','其它'];
export function vacancyDate(previous, status, observedChangeDate = null) {
  if (status !== 'vacant' || previous?.archived) return null;
  return previous?.status === 'vacant' ? previous.vacantSince || null : previous?.status === 'rented' ? observedChangeDate : null;
}
export function vacantDays(unit, today) {
  if (unit.status !== 'vacant' || !validDate(unit.vacantSince) || unit.vacantSince > today) return null;
  return Math.floor((Date.parse(today+'T00:00:00Z')-Date.parse(unit.vacantSince+'T00:00:00Z'))/86400000);
}
export function kpiMetrics(rows, column, year) {
  const amountRow = rows.find(r => new RegExp(`^${year}年(?:當月|本月)業績$`).test(String(r[0] || '').trim()));
  const rateRow = rows.find(r => /^(?:當月|每月)業績完成率/.test(String(r[0] || '').trim()));
  const occupancyRow = rows.find(r => /出租率/.test(String(r[0] || '')) && !/材積/.test(String(r[0] || '')));
  function value(row, rate=false) {
    const raw = row?.[column];
    // 尚未填寫月份的 Excel 公式可能回傳 #DIV/0!，這類資料視為缺值。
    if (raw && typeof raw === 'object' && 'error' in raw) return null;
    if (/^#(?:DIV\/0!|N\/A|VALUE!|REF!|NAME\?|NUM!|NULL!)$/.test(String(raw))) return null;
    if (raw == null || /^\s*(?:[-—–]|N[./]?A\.?)?\s*$/i.test(String(raw))) return null;
    const text = String(raw).normalize('NFKC').trim();
    const n = Number(text.replace(/[%％,\s]/g,''));
    if (!Number.isFinite(n) || n < 0) throw new Error(`KPI ${column}月「${row[0]}」數值不合法`);
    // Excel 百分比儲存為小數；文字百分比則除以 100。
    return rate ? (/%|％/.test(text) ? n : n * 100) : n;
  }
  return { revenue: value(amountRow), performance: value(rateRow,true), occupancy: value(occupancyRow,true) };
}
export function annualProgress(year, today, months, referrals, goal, branch) {
  const y=Number(year), nowY=Number(today.slice(0,4));
  const completed=y<nowY?12:y>nowY?0:Number(today.slice(5,7))-1;
  const rows=Array.from({length:completed},(_,i)=>months.find(m=>m.id===`${year}-${String(i+1).padStart(2,'0')}`||m.month===`${year}-${String(i+1).padStart(2,'0')}`));
  const metrics=rows.map(m=>m?.source==='import'?m.kpiMetrics?.performance:null);
  const complete=completed>0 && metrics.every(v=>typeof v==='number'&&Number.isFinite(v));
  const sum=metrics.reduce((n,v)=>n+(typeof v==='number'?v:0),0), remaining=12-completed;
  const average=complete?sum/completed:null;
  const required=goal?.performance!=null && (complete||completed===0) && remaining>0 ? Math.max(0,(goal.performance*12-sum)/remaining):null;
  const referred=referrals.filter(r=>r.month?.startsWith(year+'-')&&Number(r.month.slice(5,7))<=(y===nowY?Number(today.slice(5,7)):y<nowY?12:0)).reduce((n,r)=>n+r.count,0);
  const latest=[...months].filter(m=>(m.id||m.month)?.startsWith(year+'-')&&m.source==='import'&&Number((m.id||m.month).slice(5,7))<=(y===nowY?Number(today.slice(5,7)):y<nowY?12:0)).sort((a,b)=>(a.id||a.month).localeCompare(b.id||b.month)).at(-1);
  const currentYear=y===nowY;
  const total=currentYear?branch.total:latest?.total;
  const rented=currentYear?branch.rented:latest?.rented;
  const corrected=months.find(m=>(m.id||m.month)===today.slice(0,7)&&m.manualOccupancy);
  const occupancy=currentYear&&corrected?corrected.kpiMetrics.occupancy:currentYear?(total>0?rented/total*100:null):latest?.kpiMetrics?.occupancy??(total>0?rented/total*100:null);
  const final=months.find(m=>(m.id||m.month)===year+'-12'&&m.source==='import');
  const finalOccupancy=final?.kpiMetrics?.occupancy??(final?.total>0?final.rented/final.total*100:null);
  return {completed,remaining,average,required,missing:metrics.filter(v=>v==null).length,referred,referralsRequired:goal?.referrals!=null&&remaining>0?Math.max(0,(goal.referrals-referred)/remaining):null,occupancy,total,rented,unitsNeeded:goal?.occupancy!=null&&total>0?Math.max(0,(currentYear&&corrected?Math.ceil(total*Math.max(0,goal.occupancy-occupancy)/100-1e-9):Math.ceil(total*goal.occupancy/100-1e-9)-rented)):null,finalOccupancy};
}
