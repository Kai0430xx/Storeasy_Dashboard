import {validDate,taipeiDate} from './domain.js';
export const waitingStatuses = ['waiting','contacted','visit','rented','cancelled'];
export const waitingStatusLabels={waiting:'待聯絡',contacted:'已聯絡',visit:'待參觀',rented:'已承租',cancelled:'已取消'};
export const activeWaiting=row=>!row.deleting&&['waiting','contacted','visit'].includes(row.status);
export const displayWaitingDate=value=>String(value||'').replace(/-/g,'/');
export function calendarDate(value,label,legacy=''){
 const text=String(value||'').trim();
 if(!text)return '';
 const normalized=text.replace(/\//g,'-');
 if(/^20\d{2}-\d{2}-\d{2}$/.test(normalized)&&validDate(normalized))return normalized;
 if(text===legacy&&/^\d{2}\/\d{2}$/.test(text))return text;
 throw new Error(label+'請輸入有效的 YYYY/MM/DD');
}
export function expiredWaiting(row,today=taipeiDate()){return activeWaiting(row)&&!!row.expires&&validDate(row.expires)&&row.expires<=today;}
export const expiryKey=row=>'expiry:'+row.expires;
export function contactTime(){const p=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date());const v=Object.fromEntries(p.map(x=>[x.type,x.value]));return `${v.year}-${v.month}-${v.day}T${v.hour}:${v.minute}`;}
export function contactInput(raw){
 const at=String(raw.at||''),channel=String(raw.channel||''),text=String(raw.text||'').trim();
 if(!/^20\d{2}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d$/.test(at)||!validDate(at.slice(0,10)))throw new Error('備註時間不正確');
 if(!['phone','line','visit'].includes(channel))throw new Error('請選擇備註分類');
 if(!text||text.length>2000)throw new Error('備註內容請填寫 1～2000 字');
 const order=typeof raw.order==='number'&&Number.isFinite(raw.order)&&raw.order>=0&&raw.order<=999999999999999?raw.order:Date.now();
 return {at,channel,text,order};
}
/** @param {any} raw @param {any} [previous] */
export function waitingInput(raw,previous=null) {
  const text = (key, max, required=false) => {
    const value = String(raw[key] ?? '').trim();
    if ((required && !value) || value.length > max) throw new Error(`${key === 'name' ? '姓名' : key === 'items' ? '存放物品' : key}未填寫或過長`);
    return value;
  };
  const number = key => {
    if (raw[key] == null || String(raw[key]).trim() === '') return null;
    const n = Number(raw[key]);
    if (!Number.isFinite(n) || n < 0 || n > 100000000) throw new Error('需求範圍請輸入有效的非負數字');
    return n;
  };
  const phone=text('phone',4), email=text('email',254);
  const needed=calendarDate(raw.needed,'需求時間',previous?.needed||'');
  const expires=calendarDate(raw.expires,'需求到期時間');
  if(needed.length===10&&expires&&expires<needed)throw new Error('需求到期時間不可早於需求時間');
  if (phone && !/^\d{1,4}$/.test(phone)) throw new Error('電話只能輸入前四碼，最多 4 位數字');
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) throw new Error('Email 格式不正確');
  const date=text('date',10,true);
  if (!/^20\d{2}-\d{2}-\d{2}$/.test(date) || !validDate(date)) throw new Error('登記日期不正確');
  const branchIds=[...new Set(raw.branchIds || [])];
  if (branchIds.length>100 || branchIds.some(id=>typeof id!=='string'||!id||id.includes('/'))) throw new Error('候補據點不正確');
  const otherBranches=text('otherBranches',300);
  if (!branchIds.length&&!otherBranches) throw new Error('請選擇候補據點，或填寫其它據點');
  const result={date,name:text('name',80,true),phone,email,needed,expires,items:text('items',500,true),note:text('note',1000),branchIds,otherBranches,volumeMin:number('volumeMin'),volumeMax:number('volumeMax'),priceMin:number('priceMin'),priceMax:number('priceMax'),status:raw.status || 'waiting',deleting:previous?.deleting||false};
  if (!waitingStatuses.includes(result.status)) throw new Error('候補狀態不正確');
  for(const [lo,hi]of[['volumeMin','volumeMax'],['priceMin','priceMax']]) if(result[lo]!==null&&result[hi]!==null&&result[lo]>result[hi]) throw new Error('需求範圍下限不可大於上限');
  return result;
}
export function matchingVacancies(row, vacancies) {
  if(!activeWaiting(row)) return [];
  return vacancies.filter(u=>row.branchIds.includes(u.branchId)&&['volume','price'].every(k=>{
    const n=u[k], min=row[k+'Min'], max=row[k+'Max'];
    return typeof n==='number'&&Number.isFinite(n)&&(min==null||n>=min)&&(max==null||n<=max);
  }));
}
export function vacancyKey(u) {return JSON.stringify([u.branchId,u.code,u.vacantSince,u.lastEventId,u.lastEventDate]);}
