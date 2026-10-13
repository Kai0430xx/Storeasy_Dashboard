import {useEffect,useState} from 'react';
import {doc,getDoc} from 'firebase/firestore';
import {db} from './firebase';
type Row=Record<string,any>;
export default function LazyUnits({events,units,children}:{events:Row[];units:Row[];children:(u:Row[])=>React.ReactNode}){
 const [extra,setExtra]=useState<Row[]>([]),[error,setError]=useState('');
 const need=[...new Map(events.filter(e=>!e.unitSnapshot&&!units.some(u=>u.branchId===e.branchId&&u.code===e.code)).map(e=>[e.branchId+'/'+e.code,e])).values()];
 useEffect(()=>{let stopped=false;setExtra([]);setError('');Promise.all(need.map(async e=>{const s=await getDoc(doc(db,'branches',e.branchId,'units',e.code));return s.exists()?{...s.data(),branchId:e.branchId,code:e.code}:null;})).then(rows=>{if(!stopped)setExtra(rows.filter(Boolean) as Row[]);}).catch(e=>{if(!stopped)setError(e.message);});return()=>{stopped=true;};},[need.map(e=>e.branchId+'/'+e.code).join(',')]);
 return <>{error&&<p role="alert">舊倉位明細載入失敗：{error}</p>}{children([...units,...extra])}</>;
}
