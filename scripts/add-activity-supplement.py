from pathlib import Path

r = Path(__file__).resolve().parents[1]
changes = {}

p = r / 'src/main.tsx'
s = p.read_text()
if 'import ActivitySupplement from' not in s:
    anchor = '{modal.code && modal.status === "rented" && <PendingEdit unit={modal}/>}'
    assert anchor in s, '找不到倉位編輯區塊，未寫入更新'
    s = 'import ActivitySupplement from "./ActivitySupplement";\n' + s
    s = s.replace(
        anchor,
        anchor + '\n{modal.code && modal.status === "rented" && <ActivitySupplement unit={modal}/>}'
    )
    anchor = '<legend>使用活動（可複選）</legend>'
    assert anchor in s
    s = s.replace(
        anchor,
        anchor + '<p className="hint">每次承租／續約請重新選擇活動，不會自動沿用上一期。</p>'
    )
changes[p] = s

changes[r / 'src/ActivitySupplement.tsx'] = r'''
import {useEffect,useState} from 'react';
import {collection,doc,onSnapshot,query,where,runTransaction,serverTimestamp} from 'firebase/firestore';
import {auth,db} from './firebase';
type Row=Record<string,any>;

export async function supplementActivity(data:Row){
 const uid=auth.currentUser?.uid;
 if(!uid)throw Error('請先登入');
 const {branchId,code,eventId,activityId}=data;
 for(const value of [branchId,code,eventId,activityId]){
  if(typeof value!=='string'||!value||value.includes('/'))throw Error('補登資料不正確');
 }
 await runTransaction(db,async t=>{
  const b=doc(db,'branches',branchId);
  const u=doc(b,'units',code),e=doc(b,'events',eventId),a=doc(b,'activities',activityId);
  const [bs,us,es,as]=await Promise.all([t.get(b),t.get(u),t.get(e),t.get(a)]);
  const unit=us.data(),event=es.data(),activity=as.data();
  if(!bs.exists()||bs.data().importing)throw Error('據點不存在或正在匯入');
  if(!unit||unit.status!=='rented'||unit.missing||unit.lastEventId!==eventId||!event||event.voided||!['new','renew'].includes(event.type)||event.code!==code||event.unitSnapshot?.leasePeriod!==unit.leasePeriod){
   throw Error('目前租期已變更或沒有對應的承租／續約紀錄，請重新開啟倉位編輯');
  }
  if(!activity||activity.archived||activity.deleting||activity.month!==event.month){
   throw Error('活動不適用於本次承租／續約月份');
  }
  const activities=event.activities||[];
  if(activities.some((v:Row)=>v.id===activityId))throw Error('此活動已登記，無須重複補登');
  if(activities.length>=30)throw Error('每筆異動最多登記 30 個活動');
  const added={id:activityId,name:activity.name};
  t.update(e,{
   activities:[...activities,added],
   activitySupplement:{activity:added,by:uid,at:serverTimestamp()}
  });
 });
}

export default function ActivitySupplement({unit}:{unit:Row}){
 const [event,setEvent]=useState<Row|null>(null);
 const [activities,setActivities]=useState<Row[]>([]);
 const [selected,setSelected]=useState('');
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState('');
 const [loading,setLoading]=useState(true);

 useEffect(()=>{
  setEvent(null);setLoading(true);
  let stopEvent=()=>{};
  const stop=onSnapshot(doc(db,'branches',unit.branchId,'units',unit.code),s=>{
   stopEvent();setEvent(null);setSelected('');
   const current=s.data();
   if(!current||current.status!=='rented'||current.missing||!current.lastEventId){
    setLoading(false);return;
   }
   stopEvent=onSnapshot(doc(db,'branches',unit.branchId,'events',current.lastEventId),v=>{
    const e=v.data();
    setEvent(e&&!e.voided&&['new','renew'].includes(e.type)&&e.unitSnapshot?.leasePeriod===current.leasePeriod?{...e,id:v.id}:null);
    setLoading(false);
   },e=>{setMessage(e.message);setLoading(false);});
  },e=>{setMessage(e.message);setLoading(false);});
  return()=>{stop();stopEvent();};
 },[unit.branchId,unit.code]);

 useEffect(()=>{
  setActivities([]);setSelected('');
  if(!event)return;
  return onSnapshot(
   query(collection(db,'branches',unit.branchId,'activities'),where('month','==',event.month)),
   s=>setActivities(s.docs.map(d=>({...d.data(),id:d.id}))),
   e=>setMessage(e.message)
  );
 },[unit.branchId,event?.id,event?.month]);

 const existing=event?.activities||[];
 const options=activities.filter(a=>!a.archived&&!a.deleting&&!existing.some((v:Row)=>v.id===a.id));

 return <fieldset disabled={busy} className="activity-supplement">
  <legend>補登活動</legend>
  {loading?<p className="hint">正在讀取目前租期的活動…</p>:!event?
   <p className="hint">目前沒有對應本期租期的承租／續約紀錄，無法補登；匯入租期或待收款續約不會補到上一期活動。</p>:
   <>
    <p className="hint">本期{event.type==='renew'?'續約':'承租'}：{event.date}。補登僅列入 {event.month} 的活動使用明細，不增加承租、續約筆數。</p>
    <p>已登記：{existing.map((v:Row)=>v.name).join('、')||'無'}</p>
    <label>選擇補登活動
     <select aria-label="選擇補登活動" value={selected} onChange={e=>setSelected(e.target.value)}>
      <option value="">請選擇活動</option>
      {options.map(a=><option value={a.id} key={a.id}>{a.name}</option>)}
     </select>
    </label>
    {!options.length&&<p className="hint">本次異動月份沒有可補登的活動。</p>}
    <button type="button" className="secondary" disabled={!selected||busy} onClick={async()=>{
     setBusy(true);setMessage('');
     try{
      await supplementActivity({branchId:unit.branchId,code:unit.code,eventId:event.id,activityId:selected});
      setSelected('');setMessage('活動已補登');
     }catch(e){
      setMessage(e instanceof Error?e.message:String(e));
     }finally{setBusy(false);}
    }}>確認補登活動</button>
    <p className="hint">此按鈕會直接儲存活動；其它倉位欄位仍需按「確認儲存」。續約時活動不會自動沿用，須重新選擇。</p>
   </>
  }
  {message&&<p role="status">{message}</p>}
 </fieldset>;
}
'''

p = r / 'firestore.rules'
s = p.read_text()
if '// activity-supplement-v1' not in s:
    anchor = '    function removesActivity() {'
    assert anchor in s, '找不到活動規則區塊，未寫入更新'
    rule = r'''
    // activity-supplement-v1
    function addsCurrentActivity() {
     let e=resource.data;let d=request.resource.data;let r=d.activitySupplement;
     let u=get(/databases/$(database)/documents/branches/$(id)/units/$(e.code)).data;
     let a=get(/databases/$(database)/documents/branches/$(id)/activities/$(r.activity.id)).data;
     return e.type in ['new','renew'] && !e.voided && u.status=='rented' && !u.get('missing',false)
      && u.lastEventId==eventId && u.leasePeriod==e.unitSnapshot.leasePeriod
      && d.diff(e).affectedKeys().hasOnly(['activities','activitySupplement'])
      && r.keys().hasOnly(['activity','by','at']) && r.by==request.auth.uid && r.at==request.time
      && r.activity=={'id':r.activity.id,'name':a.name} && !a.archived && !a.get('deleting',false) && a.month==e.month
      && e.activities is list && d.activities is list && d.activities.size()<=30
      && !e.activities.hasAny([r.activity]) && d.activities==e.activities.concat([r.activity]);
    }
    allow update: if branchEdit(id) && unlocked(id)
      && request.resource.data.diff(resource.data).affectedKeys().hasOnly(['activities','activitySupplement'])
      && addsCurrentActivity();
'''
    s = s.replace(anchor, rule + anchor)
changes[p] = s

p = r / 'src/manual-content.ts'
s = p.read_text()
if '// activity-supplement-v1-manual' not in s:
    s += r'''
// activity-supplement-v1-manual
manualPages.find(p=>p.id==='units')?.topics.push({title:'編輯倉位補登活動與續約活動',steps:['已出租倉位點「編輯」，在「補登活動」確認本期承租／續約日期及已登記活動，選活動後按「確認補登活動」。一次補一個，可重複操作補登不同活動。','補登按鈕直接儲存活動；尺寸、月租、備註等其它欄位仍需按「確認儲存」。僅能選同據點、原異動月份且未封存的活動，已登記活動不重複計算。','續約活動預設不勾選，不沿用上一期；上一期活動保留於原月份歷史明細。待收款續約依當次所選活動於確認收款後入帳。'],result:'補登只更新本期原有異動的活動清單，不改租期、價格快照、承租／續約數量或 KPI。沒有本期承租／續約紀錄的匯入倉位、尚未入帳的待收款續約及已退租倉位不能透過此功能補登，以免誤改上一期。'});
'''
changes[p] = s

for p, s in changes.items():
    p.write_text(s, encoding='utf-8')

print('已加入本期補登活動、續約提示與操作手冊。請發布更新後的 firestore.rules。')
