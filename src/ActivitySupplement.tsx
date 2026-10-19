
import {useEffect,useState} from 'react';
import {collection,doc,getDoc,onSnapshot,query,where,runTransaction,serverTimestamp} from 'firebase/firestore';
import {auth,db} from './firebase';
import {taipeiDate} from './domain.js';
type Row=Record<string,any>;

const source=(u:Row)=>u.lastEventId||null;
const key=(code:string,id:string,u:Row)=>`activity-${code}-${id}-${source(u)}-${u.leaseStart??null}-${u.leaseEnd??null}`;

export async function supplementActivity(data:Row){
 const uid=auth.currentUser?.uid;
 if(!uid)throw Error('請先登入');
 const {branchId,code,activityId}=data;
 for(const v of [branchId,code,activityId]){
  if(typeof v!=='string'||!v||v.includes('/'))throw Error('補登資料不正確');
 }
 const date=taipeiDate(),month=date.slice(0,7);
 const b=doc(db,'branches',branchId),u=doc(b,'units',code);
 const initial=(await getDoc(u)).data();
 if(!initial)throw Error('倉位不存在');
 const e=doc(b,'events',key(code,activityId,initial));
 const a=doc(b,'activities',activityId);

 await runTransaction(db,async t=>{
  const [bs,us,es,as,previous]=await Promise.all([
   t.get(b),t.get(u),t.get(e),t.get(a),
   source(initial)?t.get(doc(b,'events',source(initial))):Promise.resolve(null)
  ]);
  const unit=us.data(),activity=as.data(),original=previous?.data();
  if(!bs.exists()||bs.data().importing)throw Error('據點不存在或正在匯入');
  if(!unit||unit.status!=='rented'||unit.missing){
   throw Error('只可為目前已出租的倉位補登活動');
  }
  if(key(code,activityId,unit)!==e.id||unit.leasePeriod!==initial.leasePeriod){
   throw Error('租期已變更，請重新開啟編輯');
  }
  if(!activity||activity.archived||activity.deleting||activity.month!==month){
   throw Error('請選擇該據點當月的活動');
  }
  if(es.exists()||original&&!original.voided&&original.month===month&&original.unitSnapshot?.leasePeriod===unit.leasePeriod&&original.activities?.some((v:Row)=>v.id===activityId)){
   throw Error('此活動已登記，無須重複補登');
  }
  const snapshot={
   dimensions:unit.dimensions||'',
   volume:unit.volume??0,
   price:unit.price??0,
   note:unit.note||'',
   leasePeriod:unit.leasePeriod||''
  };
  t.set(e,{
   type:'activitySupplement',code,date,month,activityId,
   sourceEventId:source(unit),
   activities:[{id:activityId,name:activity.name}],
   unitSnapshot:snapshot,
   createdBy:uid,createdAt:serverTimestamp(),voided:false
  });
 });
}

export default function ActivitySupplement({unit}:{unit:Row}){
 const [current,setCurrent]=useState<Row|null>(null);
 const [activities,setActivities]=useState<Row[]>([]);
 const [events,setEvents]=useState<Row[]>([]);
 const [selected,setSelected]=useState('');
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState('');
 const [loading,setLoading]=useState(true);
 const [month,setMonth]=useState(()=>taipeiDate().slice(0,7));

 useEffect(()=>{
  const timer=setInterval(()=>setMonth(taipeiDate().slice(0,7)),30000);
  return()=>clearInterval(timer);
 },[]);

 useEffect(()=>{
  setLoading(true);setCurrent(null);setActivities([]);
  setEvents([]);setSelected('');setMessage('');
  const error=(e:Error)=>{setMessage(e.message);setLoading(false);};
  const stops=[
   onSnapshot(doc(db,'branches',unit.branchId,'units',unit.code),s=>{
    setCurrent(s.exists()?s.data():null);
    setLoading(false);
   },error),
   onSnapshot(
    query(collection(db,'branches',unit.branchId,'activities'),where('month','==',month)),
    s=>setActivities(s.docs.map(d=>({...d.data(),id:d.id}))),
    error
   ),
   onSnapshot(
    query(collection(db,'branches',unit.branchId,'events'),where('month','==',month)),
    s=>setEvents(s.docs.map(d=>({...d.data(),id:d.id}))),
    error
   )
  ];
  return()=>stops.forEach(stop=>stop());
 },[unit.branchId,unit.code,month]);

 const uses=current?events.filter(e=>
  e.code===unit.code&&!e.voided
  &&e.unitSnapshot?.leasePeriod===(current.leasePeriod||'')
  &&(e.type==='activitySupplement'
   ?e.sourceEventId===source(current)
   :e.id===source(current))
 ).flatMap(e=>e.activities||[]):[];

 const existing=[...new Map(uses.map((a:Row)=>[a.id,a])).values()] as Row[];
 const options=activities.filter(a=>
  !a.archived&&!a.deleting&&!existing.some(v=>v.id===a.id)
 );

 return <fieldset disabled={busy} className="activity-supplement">
  <legend>補登活動</legend>
  <p className="hint">直接選擇該據點當月（{month}）活動，匯入的已出租倉位也可以補登。</p>
  {loading?<p className="hint">讀取中…</p>:
   !current||current.status!=='rented'||current.missing?
   <p className="hint">只可為目前已出租的倉位補登活動。</p>:
   <>
    <p>本期當月已登記：{existing.map(v=>v.name).join('、')||'無'}</p>
    <label>選擇補登活動
     <select aria-label="選擇補登活動" value={selected} onChange={e=>setSelected(e.target.value)}>
      <option value="">請選擇當月活動</option>
      {options.map(a=><option value={a.id} key={a.id}>{a.name}</option>)}
     </select>
    </label>
    {!options.length&&<p className="hint">當月沒有可補登的活動，或活動已登記。</p>}
    <button type="button" className="secondary" disabled={!selected||busy} onClick={async()=>{
     setBusy(true);setMessage('');
     try{
      await supplementActivity({
       branchId:unit.branchId,code:unit.code,activityId:selected
      });
      setSelected('');setMessage('當月活動已補登');
     }catch(e){
      setMessage(e instanceof Error?e.message:String(e));
     }finally{setBusy(false);}
    }}>確認補登活動</button>
    <p className="hint">按鈕直接儲存活動；其它倉位欄位仍需按「確認儲存」。不增加承租／續約筆數，不改租期。續約不會沿用上一期活動。</p>
   </>
  }
  {message&&<p role="status">{message}</p>}
 </fieldset>;
}
