
import {useEffect,useState} from 'react';

export default function useInitialBranch(
 uid:string|undefined,
 profile:any,
 branches:any[],
 setBranchId:(id:string)=>void
){
 const [initialized,setInitialized]=useState('');
 const scope=JSON.stringify(
  branches.filter(b=>!b.archived).map(b=>b.id)
 );

 useEffect(()=>{
  if(!uid){
   if(initialized)setInitialized('');
   return;
  }
  if(!profile||initialized===uid)return;

  const available=branches.filter(b=>!b.archived);
  if(!available.length)return;

  const own=(profile.branchIds||[])
   .map((id:string)=>available.find(b=>b.id===id))
   .find(Boolean);

  setBranchId((own||available[0]).id);
  setInitialized(uid);
 },[
  uid,profile?.role,JSON.stringify(profile?.branchIds),
  scope,initialized
 ]);

 return !!uid&&initialized===uid;
}
