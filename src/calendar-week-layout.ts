import type {CalRow} from './calendar-client';
// Reserve a whole horizontal lane for each visible segment; never split it by day.
export function calendarWeekLayout(events:CalRow[],dates:string[]){
 const occupied=Array.from({length:3},()=>Array(7).fill(false));
 const hidden=Array(7).fill(0);
 const candidates=events.filter(e=>e.startDate<=dates[6]&&e.endDate>=dates[0]).map(event=>({
  event,start:dates.findIndex(d=>d>=event.startDate),end:6-[...dates].reverse().findIndex(d=>d<=event.endDate)
 })).sort((a,b)=>(b.end-b.start)-(a.end-a.start)||Number(b.event.allDay)-Number(a.event.allDay)||a.event.startDate.localeCompare(b.event.startDate)||(a.event.startTime||'').localeCompare(b.event.startTime||'')||a.event.id.localeCompare(b.event.id));
 const segments=[];
 for(const candidate of candidates){
  const {start,end,event}=candidate;
  const lane=occupied.findIndex(row=>row.slice(start,end+1).every(value=>!value));
  if(lane<0){for(let day=start;day<=end;day++)hidden[day]++;continue;}
  for(let day=start;day<=end;day++)occupied[lane][day]=true;
  segments.push({...candidate,lane,showTitle:event.startDate>=dates[0],continuesBefore:event.startDate<dates[0],continuesAfter:event.endDate>dates[6]});
 }
 return {segments,hidden};
}
