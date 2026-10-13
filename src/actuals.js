export function effectiveMonths(months, actuals = []) {
 const result=months.map(m=>({...m,kpiMetrics:{...m.kpiMetrics}}));
 for(const a of actuals){if(a.occupancy==null&&a.performance==null)continue;let m=result.find(v=>(v.id||v.month)===(a.id||a.month));if(!m){m={id:a.id||a.month,month:a.month,kpiMetrics:{}};result.push(m);}m.source='import';m.manualActuals=true;m.manualOccupancy=a.occupancy!=null;for(const k of ['occupancy','performance'])if(a[k]!=null)m.kpiMetrics[k]=a[k];}
 return result;
}
