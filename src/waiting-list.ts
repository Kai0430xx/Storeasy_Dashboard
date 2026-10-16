import {useEffect,useMemo,useState} from 'react';
import {collection,collectionGroup,doc,onSnapshot,query,where,or,getDocs,getDoc,setDoc,writeBatch,serverTimestamp,runTransaction} from 'firebase/firestore';
import {auth,db} from './firebase';
import {matchingVacancies,vacancyKey,waitingInput,expiredWaiting,expiryKey,activeWaiting,contactInput} from './waiting-domain.js';
import {stockData} from './waiting-stock';
import {taipeiDate} from './domain.js';
export type WaitingRow=Record<string,any>;
const message=(e:any)=>e.code==='permission-denied'?'候補清單權限遭拒，請先發布最新 Firebase 規則後重新整理。':e.message||'操作失敗';
export function useWaitingList(profile:WaitingRow|null,branches:WaitingRow[],initialize:boolean){
 const [today,setToday]=useState(taipeiDate());
 useEffect(()=>{const refresh=()=>setToday(taipeiDate());const timer=window.setInterval(refresh,30000);window.addEventListener('focus',refresh);document.addEventListener('visibilitychange',refresh);return()=>{clearInterval(timer);window.removeEventListener('focus',refresh);document.removeEventListener('visibilitychange',refresh);};},[]);
 const [archived,setArchived]=useState<string[]>([]);
 const [rows,setRows]=useState<WaitingRow[]>([]),[stock,setStock]=useState<WaitingRow[]>([]),[reads,setReads]=useState<Record<string,string[]>>({}),[error,setError]=useState(''),[syncError,setSyncError]=useState(''),[ready,setReady]=useState(false),[syncing,setSyncing]=useState(false),[retry,setRetry]=useState(0);
 const uid=auth.currentUser?.uid,enabled=!!uid&&['admin','supervisor','manager'].includes(profile?.role),global=profile&&['admin','supervisor'].includes(profile.role);
 const scope=JSON.stringify([uid,profile?.role,profile?.branchIds||[]]);
 useEffect(()=>{
  setRows([]);setStock([]);setArchived([]);setReads({});setError('');setReady(false);
  if(!enabled)return;
  const groups:WaitingRow[][]=[];let listReady=false,stockReady=false,readsReady=false;const seen=new Set<number>();
  const updateReady=()=>setReady(listReady&&stockReady&&readsReady);
  const stops:(()=>void)[]=[];
  const ids=profile?.branchIds||[];
  const sources=global?[collection(db,'waitingList')]:Array.from({length:Math.max(1,Math.ceil(ids.length/29))},(_,i)=>{
   const group=ids.slice(i*29,i*29+29);
   return group.length?query(collection(db,'waitingList'),or(where('createdBy','==',uid),where('branchIds','array-contains-any',group))):query(collection(db,'waitingList'),where('createdBy','==',uid));
  });
  const fail=(e:any)=>{setError(message(e));setReady(false);};
  sources.forEach((q,i)=>stops.push(onSnapshot(q,s=>{groups[i]=s.docs.map(d=>({id:d.id,...d.data()}));setRows([...new Map(groups.flat().map(r=>[r.id,r])).values()].sort((a,b)=>b.date.localeCompare(a.date)||b.id.localeCompare(a.id)));seen.add(i);listReady=seen.size===sources.length;updateReady();},fail)));
  stops.push(onSnapshot(collection(db,'workBranches'),s=>setArchived(s.docs.filter(d=>d.data().archived).map(d=>d.id)),fail));
  stops.push(onSnapshot(collectionGroup(db,'waitingUnits'),s=>{setStock(s.docs.map(d=>d.data()));stockReady=true;updateReady();},fail));
  stops.push(onSnapshot(collection(db,'waitingReads',uid!,'items'),s=>{setReads(Object.fromEntries(s.docs.map(d=>[d.id,d.data().seen||[]])));readsReady=true;updateReady();},fail));
  return()=>stops.forEach(stop=>stop());
 },[scope]);
 const branchScope=JSON.stringify(branches.filter(b=>!b.archived&&!b.importing).map(b=>b.id).sort());
 useEffect(()=>{
  if(!enabled||!initialize)return;
  let active=true;setSyncing(true);setSyncError('');
  (async()=>{
   for(const id of JSON.parse(branchScope)){
    const marker=doc(db,'waitingStock',id);if((await getDoc(marker)).data()?.initialized)continue;
    const source=await getDocs(query(collection(db,'branches',id,'units'),where('status','==','vacant')));
    const old=await getDocs(collection(marker,'waitingUnits'));
    const desired=new Map<string,WaitingRow>();for(const s of source.docs){const u=stockData(s.ref.path,s.data());if(u)desired.set(s.id,u);}
    const changes=[...desired.entries()].map(([code,data])=>({ref:doc(marker,'waitingUnits',code),data})).concat(old.docs.filter(d=>!desired.has(d.id)).map(d=>({ref:d.ref,data:null as any})));
    for(let i=0;i<changes.length;i+=8){const batch=writeBatch(db);for(const change of changes.slice(i,i+8)){if(change.data)batch.set(change.ref,change.data);else batch.delete(change.ref);}await batch.commit();}
    await setDoc(marker,{initialized:true});
   }
  })().catch(e=>{if(active)setSyncError(message(e));}).finally(()=>{if(active)setSyncing(false);});
  return()=>{active=false;};
 },[scope,branchScope,initialize,retry]);
 const blocked=JSON.stringify([...archived,...branches.filter(b=>b.importing).map(b=>b.id)].sort());
 const availableStock=useMemo(()=>stock.filter(u=>!JSON.parse(blocked).includes(u.branchId)),[stock,blocked]);
 const matches=useMemo(()=>Object.fromEntries(rows.map(r=>[r.id,matchingVacancies(r,availableStock)])),[rows,availableStock]);
 const isExpired=(row:WaitingRow)=>expiredWaiting(row,today);
 const notification=(row:WaitingRow)=>{
  if(!ready||!activeWaiting(row))return null;
  const seen=reads[row.id]||[];
  if(isExpired(row)&&!seen.includes(expiryKey(row)))return 'red';
  if((row.createdBy!==uid&&!Object.hasOwn(reads,row.id))||(matches[row.id]||[]).some((u:WaitingRow)=>!seen.includes(vacancyKey(u))))return 'yellow';
  return null;
 };
 const unread=(row:WaitingRow)=>notification(row)!==null;
 const alertTone=rows.some(r=>notification(r)==='red')?'red':rows.some(unread)?'yellow':null;

 async function markRead(row:WaitingRow){
  if(!uid||!ready)return;
  const keys=['created',...(matches[row.id]||[]).map(vacancyKey),...(isExpired(row)?[expiryKey(row)]:[])];
  const ref=doc(db,'waitingReads',uid,'items',row.id);
  try{await runTransaction(db,async tx=>{const old=await tx.get(ref);const seen=[...new Set([...(old.data()?.seen||[]),...keys])].slice(-2000);tx.set(ref,{seen});});}catch(e){setError(message(e));}
 }
 return {rows,stock:availableStock,matches,unread,notification,isExpired,alertTone,hasUnread:rows.some(unread),markRead,ready,error,syncError,syncing,retrySync:()=>setRetry(n=>n+1)};
}
export async function saveWaiting(raw:WaitingRow,id?:string,revision?:number){
 const uid=auth.currentUser?.uid;if(!uid)throw new Error('請先登入');
 const drafts=(raw.noteDrafts||[]).map(contactInput);
 if(drafts.length>30)throw new Error('每次最多新增 30 筆備註');
 const ref=id?doc(db,'waitingList',id):doc(collection(db,'waitingList'));
 const noteRefs=drafts.map(()=>doc(collection(ref,'notes')));
 await runTransaction(db,async tx=>{
  const old=await tx.get(ref);
  if(id&&(!old.exists()||old.data().revision!==revision))throw new Error('這筆候補已被修改或刪除，請關閉後重新開啟');
  if(old.data()?.deleting)throw new Error('這筆候補正在刪除，請先完成刪除');
  const clean=waitingInput(raw,old.data()||null);
  const stamp=serverTimestamp();tx.set(ref,{...clean,createdBy:old.data()?.createdBy||uid,createdAt:old.data()?.createdAt||stamp,updatedBy:uid,updatedAt:stamp,revision:(old.data()?.revision||0)+1});
  drafts.forEach((note:any,i:number)=>tx.set(noteRefs[i],{...note,createdBy:uid,createdAt:stamp}));
 });return ref.id;
}
export async function deleteWaiting(row:WaitingRow){
 const ref=doc(db,'waitingList',row.id),uid=auth.currentUser?.uid;
 if(!uid)throw new Error('請先登入');
 await runTransaction(db,async tx=>{const s=await tx.get(ref);if(!s.exists())return;if(s.data().deleting)return;if(s.data().revision!==row.revision)throw new Error('資料已被修改，請重新確認後刪除');tx.update(ref,{deleting:true,revision:s.data().revision+1,updatedBy:uid,updatedAt:serverTimestamp()});});
 const children=await getDocs(collection(ref,'notes'));
 for(let i=0;i<children.docs.length;i+=100){const batch=writeBatch(db);children.docs.slice(i,i+100).forEach(d=>batch.delete(d.ref));await batch.commit();}
 await runTransaction(db,async tx=>{const s=await tx.get(ref);if(s.exists()&&s.data().deleting)tx.delete(ref);});
}

export async function addWaitingNote(id:string,raw:WaitingRow){
 const uid=auth.currentUser?.uid;if(!uid)throw new Error('請先登入');
 const clean=contactInput(raw),parent=doc(db,'waitingList',id),ref=doc(collection(parent,'notes'));
 await runTransaction(db,async tx=>{const root=await tx.get(parent);if(!root.exists()||root.data().deleting)throw new Error('候補紀錄已刪除或正在刪除');tx.set(ref,{...clean,createdBy:uid,createdAt:serverTimestamp()});});
}
