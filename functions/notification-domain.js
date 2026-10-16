
import {ECDH} from 'node:crypto';

export const roles = ['admin','supervisor','manager'];
export const enabled = p => roles.includes(p?.role);
export const globalProfile = p => ['admin','supervisor'].includes(p?.role);
export const intersects = (a=[],b=[]) => a.some(id=>b.includes(id));
export const millis = v => Number(
  v?.toMillis?.() ??
  (v?.seconds!=null
    ? v.seconds*1000+Math.floor((v.nanoseconds||0)/1e6)
    : v||0)
)||0;

export const day = () => new Intl.DateTimeFormat('en-CA',{
  timeZone:'Asia/Taipei',
  year:'numeric',
  month:'2-digit',
  day:'2-digit'
}).format(new Date());

export function workVisible(task,uid,p,assignment){
  return enabled(p)&&(
    globalProfile(p)||
    task.createdBy===uid||
    intersects(task.branchIds,p.branchIds)||
    !!assignment
  );
}

export const workNotificationVisible = (
  task,uid,p,assignment=false
) => enabled(p)&&(
  globalProfile(p)
    ? (task.directAssigneeIds||[]).includes(uid)||assignment
    : workVisible(task,uid,p,assignment)
);

export const waitingNotificationVisible = (row,uid,p) =>
  enabled(p)&&intersects(row.branchIds,p.branchIds);

export const calendarDate = s =>
  /^20\d{2}-\d{2}-\d{2}$/.test(s||'')&&
  !Number.isNaN(Date.parse(s+'T00:00:00Z'))&&
  new Date(s+'T00:00:00Z').toISOString().slice(0,10)===s;

export const vacancyKey = u => JSON.stringify([
  u.branchId,u.code,u.vacantSince,u.lastEventId,u.lastEventDate
]);

export function workUnread(tasks,reads,uid){
  const keys=[];
  for(const task of tasks){
    const threads=[];
    for(const [thread,signals] of Object.entries(task.signals||{})){
      if(task.deleted&&thread!=='main')continue;
      const unseen=Object.entries(signals).filter(
        ([actor,time])=>
          actor!==uid&&
          millis(time)>millis(reads[task.id]?.seen?.[thread])
      );
      if(unseen.length){
        threads.push([
          thread,
          unseen.map(([actor,time])=>[actor,millis(time)]).sort()
        ]);
      }
    }
    if(threads.length){
      keys.push(JSON.stringify([task.id,threads.sort()]));
    }
  }
  return {count:keys.length,keys:keys.sort()};
}

export function waitingUnread(rows,stock,reads,uid,today=day()){
  const keys=[];
  for(const row of rows){
    if(row.deleting||
       !['waiting','contacted','visit'].includes(row.status))continue;

    const seen=reads[row.id]||[];
    const alerts=[];

    if(calendarDate(row.expires)&&
       row.expires<=today&&
       !seen.includes('expiry:'+row.expires)){
      alerts.push('expiry:'+row.expires);
    }

    if(row.createdBy!==uid&&!Object.hasOwn(reads,row.id)){
      alerts.push('created');
    }

    for(const u of stock){
      if(!(row.branchIds||[]).includes(u.branchId))continue;
      if(!['volume','price'].every(k=>
        typeof u[k]==='number'&&Number.isFinite(u[k])&&
        (row[k+'Min']==null||u[k]>=row[k+'Min'])&&
        (row[k+'Max']==null||u[k]<=row[k+'Max'])
      ))continue;

      const key=vacancyKey(u);
      if(!seen.includes(key))alerts.push(key);
    }

    if(alerts.length){
      keys.push(JSON.stringify([
        row.id,[...new Set(alerts)].sort()
      ]));
    }
  }
  return {count:keys.length,keys:keys.sort()};
}

export function validSubscription(raw){
  try{
    const url=new URL(raw.endpoint);
    const hosts=[
      'fcm.googleapis.com',
      'android.googleapis.com',
      'web.push.apple.com'
    ];

    if(url.protocol!=='https:'||
       url.username||url.password||url.port||url.hash||
       raw.endpoint.length>4096||
       !(hosts.includes(url.hostname)||
         url.hostname.endsWith('.push.apple.com')||
         url.hostname.endsWith('.push.services.mozilla.com')||
         url.hostname.endsWith('.notify.windows.com'))){
      return false;
    }

    if(typeof raw.keys.p256dh!=='string'||
       raw.keys.p256dh.length>90||
       typeof raw.keys.auth!=='string'||
       raw.keys.auth.length>24)return false;

    ECDH.convertKey(
      Buffer.from(raw.keys.p256dh,'base64url'),
      'prime256v1',undefined,undefined,'uncompressed'
    );

    return /^[A-Za-z0-9_-]+={0,2}$/.test(raw.keys.p256dh)&&
      /^[A-Za-z0-9_-]+={0,2}$/.test(raw.keys.auth)&&
      Buffer.from(raw.keys.p256dh,'base64url').length===65&&
      Buffer.from(raw.keys.auth,'base64url').length===16;
  }catch{
    return false;
  }
}
