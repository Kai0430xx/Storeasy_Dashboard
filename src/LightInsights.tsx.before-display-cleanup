import {useEffect,useRef,useState} from 'react';
import {collection,getDocs,query,where} from 'firebase/firestore';
import {db} from './firebase';
import {exitCategories,vacantDays} from './targets.js';
import {taipeiDate} from './domain.js';
type Row=Record<string,any>;
export default function LightInsights({branches,events,month}:{branches:Row[];events:Row[];month:string}){
 const [units,setUnits]=useState<Row[]|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[loadedAt,setLoadedAt]=useState('');
 const generation=useRef(0);
 useEffect(()=>{generation.current++;setUnits(null);setError('');setLoadedAt('');setBusy(false);return()=>{generation.current++;};},[branches.map(b=>b.id).join(','),month]);
 async function load(){const request=++generation.current;setBusy(true);setError('');try{const rows=await Promise.all(branches.filter(b=>b.vacant>0).map(async b=>{const s=await getDocs(query(collection(db,'branches',b.id,'units'),where('status','==','vacant')));return s.docs.map(d=>d.data());}));if(request!==generation.current)return;setUnits(rows.flat());setLoadedAt(new Date().toLocaleString('zh-TW',{timeZone:'Asia/Taipei'}));}catch(e){if(request===generation.current)setError(e instanceof Error?e.message:String(e));}finally{if(request===generation.current)setBusy(false);}}
 const vacant=units?.filter(u=>u.status==='vacant'&&!u.archived&&!u.missing),today=taipeiDate(),exits=events.filter(e=>e.type==='exit'&&!e.voided);
 return <section className="panel target-panel"><h2>空倉與退租概況</h2><p>目前空倉 {branches.reduce((n,b)=>n+Number(b.vacant||0),0)} 間</p><button disabled={busy||!branches.length} onClick={load}>{busy?'載入中…':units?'更新空倉天數統計':'查看空倉天數統計'}</button>{error&&<p role="alert">{error}</p>}{vacant&&<><p>資料取得時間：{loadedAt}・起始日未記錄 {vacant.filter(u=>vacantDays(u,today)==null).length} 間</p><p>空置至少 30 天：{vacant.filter(u=>(vacantDays(u,today)??-1)>=30).length} 間・至少 60 天：{vacant.filter(u=>(vacantDays(u,today)??-1)>=60).length} 間・至少 90 天：{vacant.filter(u=>(vacantDays(u,today)??-1)>=90).length} 間（區間包含較長天數）</p></>}<h3>所選月份退租原因</h3>{[...exitCategories,'未分類'].map(c=><span className="badge" key={c}>{c}：{exits.filter(e=>(e.exitCategory||'未分類')===c).length} 筆 </span>)}</section>;
}
