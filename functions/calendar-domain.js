export const calendarRoles=['admin','supervisor','manager','employee'];
export const globalCalendar=p=>['admin','supervisor'].includes(p?.role);
export const calendarEnabled=p=>calendarRoles.includes(p?.role);
export const dateOK=s=>/^\d{4}-\d{2}-\d{2}$/.test(s||'')&&!Number.isNaN(Date.parse(s+'T00:00:00Z'))&&new Date(s+'T00:00:00Z').toISOString().slice(0,10)===s;
export const addDays=(s,n)=>new Date(Date.parse(s+'T00:00:00Z')+n*86400000).toISOString().slice(0,10);
export const dayDiff=(a,b)=>Math.round((Date.parse(b+'T00:00:00Z')-Date.parse(a+'T00:00:00Z'))/86400000);
export function calendarMonths(e){const keys=[];let m=e.startDate.slice(0,7),last=e.endDate.slice(0,7);while(m<=last&&keys.length<14){keys.push(m);const [y,n]=m.split('-').map(Number);m=n===12?`${y+1}-01`:`${y}-${String(n+1).padStart(2,'0')}`;}return keys;}
export const eventFields=['title','startDate','endDate','endDateUnset','startTime','endTime','allDay','categoryId','notes','viewerIds'];
export function eventInput(raw){
 const title=String(raw.title||'').trim(),notes=String(raw.notes||'');
 const startDate=String(raw.startDate||''),endDateUnset=raw.endDateUnset===true||!raw.endDate,endDate=endDateUnset?startDate:String(raw.endDate),allDay=raw.allDay===true;
 const startTime=allDay?'':String(raw.startTime||''),endTime=allDay?'':String(raw.endTime||'');
 if(!title||title.length>120||notes.length>5000)throw Error('標題須為1～120字，備註最多5000字');
 if(!dateOK(startDate)||!dateOK(endDate)||startDate<'2000-01-01'||endDate>'2099-12-31'||endDate<startDate||dayDiff(startDate,endDate)>365)throw Error('日期不合法，單筆行程最長366天');
 if(!allDay&&(!/^([01]\d|2[0-3]):[0-5]\d$/.test(startTime)||endTime&&(!/^([01]\d|2[0-3]):[0-5]\d$/.test(endTime)||startDate===endDate&&endTime<=startTime)))throw Error('請填寫正確開始時間；若填結束時間，須晚於開始');
 if(!Array.isArray(raw.viewerIds)||raw.viewerIds.length>100||raw.viewerIds.some(x=>typeof x!=='string'||!x||x.includes('/')))throw Error('分享對象不合法或超過100人');
 return {title,notes,startDate,endDate,endDateUnset,startTime,endTime,allDay,categoryId:String(raw.categoryId||''),viewerIds:[...new Set(raw.viewerIds)].sort()};
}
export const visibleEvent=(e,uid,p)=>calendarEnabled(p)&&(globalCalendar(p)||e.ownerId===uid||(e.viewerIds||[]).includes(uid));
export const activeEvent=e=>e&&!e.removed&&!e.sourceDeleted;
export const calendarAlert=(r,uid)=>r.ownerId===uid&&r.status==='pending'||r.requesterId===uid&&r.status!=='pending'&&!r.seen;
