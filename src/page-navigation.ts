import {useCallback,useEffect,useState} from 'react';

const pages = ['dashboard','units','activities','imports','targets','waiting','work','users','manual'];

function readPage(){
 const page = window.location.hash.slice(1);
 return pages.includes(page) ? page : 'dashboard';
}

function allowed(page:string,role:string){
 if(role==='pending')return ['dashboard','manual'].includes(page);
 if(page==='users')return ['admin','supervisor'].includes(role);
 if(['waiting','work'].includes(page))return ['admin','supervisor','manager'].includes(role);
 return pages.includes(page);
}

export function usePageNavigation(role?:string){
 const [page,setPage] = useState(readPage);

 useEffect(()=>{
  const sync = ()=>setPage(readPage());
  window.addEventListener('hashchange',sync);
  return ()=>window.removeEventListener('hashchange',sync);
 },[]);

 useEffect(()=>{
  if(!role)return;
  const next = allowed(page,role) ? page : 'dashboard';
  if(next!==page)setPage(next);
  if(window.location.hash!=='#'+next){
   window.history.replaceState(
    null,'',
    window.location.pathname+window.location.search+'#'+next
   );
  }
 },[page,role]);

 const navigate = useCallback((next:string)=>{
  const target = pages.includes(next) && (!role || allowed(next,role))
   ? next : 'dashboard';
  setPage(target);
  if(window.location.hash!=='#'+target)window.location.hash=target;
 },[role]);

 return [page,navigate] as const;
}
