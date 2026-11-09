import {useEffect,useState} from 'react';
import {collection,onSnapshot,query,where} from 'firebase/firestore';
import {getFunctions,httpsCallable} from 'firebase/functions';
import {auth,db} from './firebase';
import './push-client';
export type CalRow=Record<string,any>;
export const calendarCall=async(data:CalRow)=>(await httpsCallable(getFunctions(undefined,'asia-east1'),'calendarAction')(data)).data as CalRow;
export const calToday=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
export const plusDays=(s:string,n:number)=>new Date(Date.parse(s+'T12:00:00Z')+n*86400000).toISOString().slice(0,10);
export const calError=(e:any)=>String(e?.message||e||'日曆操作失敗，請重試');
export function useCalendarAlerts(uid:string|undefined,enabled:boolean){
 const [rows,setRows]=useState<CalRow[]>([]),[error,setError]=useState('');
 useEffect(()=>{setRows([]);setError('');if(!uid||!enabled)return;const parts=new Map<number,CalRow[]>();const stops=['ownerId','requesterId'].map((field,i)=>onSnapshot(query(collection(db,'calendarRequests'),where(field,'==',uid)),snapshot=>{parts.set(i,snapshot.docs.map(d=>({id:d.id,...d.data()})));setRows([...new Map([...parts.values()].flat().map(r=>[r.id,r])).values()]);},e=>setError(calError(e))));return()=>stops.forEach(stop=>stop());},[uid,enabled]);
 const pending=rows.filter(r=>r.ownerId===uid&&r.status==='pending');
 const unread=rows.filter(r=>r.ownerId===uid&&r.status==='pending'||r.requesterId===uid&&r.status!=='pending'&&!r.seen);
 return {rows,pending,unread,count:unread.length,error};
}
export const freshCalendar=(date=calToday()):CalRow=>({id:'evt_'+crypto.randomUUID(),title:'',startDate:date,endDate:'',endDateUnset:true,startTime:'09:00',endTime:'',allDay:false,categoryId:'',notes:'',viewerIds:[],revision:0});
export async function createWorkOnCalendar(profile:CalRow,input:CalRow){
 const result=await calendarCall({action:'createWork',operationId:input.calendarDraft.operationId,task:input});return result.count as number;
}
export function useCalendarDirectory(){const [people,setPeople]=useState<CalRow[]>([]),[error,setError]=useState('');useEffect(()=>{let alive=true;void calendarCall({action:'directory'}).then(r=>{if(alive)setPeople(r.people||[]);}).catch(e=>{if(alive)setError(calError(e));});return()=>{alive=false;};},[]);return {people,error};}
export function useCalendarCategories(ownerId:string|undefined,eventId?:string){
 const [rows,setRows]=useState<CalRow[]>([]),[error,setError]=useState('');
 useEffect(()=>{
  setRows([]);setError('');if(!ownerId)return;
  if(ownerId!==auth.currentUser?.uid){
   let live=true;if(!eventId){setError('缺少行程，無法讀取分類');return;}
   void calendarCall({action:'categoryOptions',ownerId,eventId}).then(r=>{if(live)setRows(r.rows||[]);}).catch(e=>{if(live)setError(calError(e));});return()=>{live=false;};
  }
  return onSnapshot(query(collection(db,'calendarCategories'),where('ownerId','==',ownerId)),s=>setRows(s.docs.map(d=>({id:d.id,...d.data()}))),e=>setError(calError(e)));
 },[ownerId,eventId]);return {rows,error};
}
