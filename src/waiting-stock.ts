import {doc,runTransaction as originalTransaction,writeBatch as originalBatch} from 'firebase/firestore';
import type {Firestore,Transaction,TransactionOptions,WriteBatch} from 'firebase/firestore';

type Row=Record<string,any>;
export const unitPath=(path:string)=>/^branches\/[^/]+\/units\/[^/]+$/.test(path);

export function stockRef(db:Firestore,path:string){
 const p=path.split('/');
 return doc(db,'waitingStock',p[1],'waitingUnits',p[3]);
}

export function stockData(path:string,u:Row|null){
 if(!u||u.status!=='vacant'||u.missing||u.archived)return null;
 const p=path.split('/');
 return {
  branchId:p[1],
  code:p[3],
  volume:u.volume,
  price:u.price,
  vacantSince:u.vacantSince??null,
  lastEventId:u.lastEventId??null,
  lastEventDate:u.lastEventDate??null
 };
}

export function runTransaction<T>(
 db:Firestore,
 fn:(t:Transaction)=>Promise<T>,
 options?:TransactionOptions
):Promise<T>{
 return originalTransaction(db,async original=>{
  const cache=new Map<string,Row|null>();
  const writes:{method:string;args:any[]}[]=[];

  const wrapped=new Proxy(original,{
   get(target,key){
    if(key==='get'){
     return async(ref:any)=>{
      const s=await original.get(ref);
      cache.set(ref.path,s.exists()?s.data() as Row:null);
      return s;
     };
    }
    if(['set','update','delete'].includes(String(key))){
     return(...args:any[])=>{
      writes.push({method:String(key),args});
      return wrapped;
     };
    }
    const value=(target as any)[key];
    return typeof value==='function'?value.bind(target):value;
   }
  }) as Transaction;

  const result=await fn(wrapped);

  for(const w of writes){
   if(unitPath(w.args[0].path)&&!cache.has(w.args[0].path)){
    const s=await original.get(w.args[0]);
    cache.set(w.args[0].path,s.exists()?s.data() as Row:null);
   }
  }

  const touched=new Set<string>();
  for(const w of writes){
   (original as any)[w.method](...w.args);
   const path=w.args[0].path;
   if(!unitPath(path))continue;

   touched.add(path);
   const old=cache.get(path);
   if(w.method==='delete')cache.set(path,null);
   else if(w.method==='update'||w.args[2]?.merge){
    cache.set(path,{...old,...w.args[1]});
   }else{
    cache.set(path,w.args[1]);
   }
  }

  for(const path of touched){
   const data=stockData(path,cache.get(path)||null);
   const ref=stockRef(db,path);
   if(data)original.set(ref,data);
   else original.delete(ref);
  }
  return result;
 },options);
}

export function writeBatch(db:Firestore):WriteBatch{
 const original=originalBatch(db);
 const wrapped=new Proxy(original,{
  get(target,key){
   if(['set','update','delete'].includes(String(key))){
    return(...args:any[])=>{
     (original as any)[key](...args);

     if(unitPath(args[0].path)){
      const u=args[1];
      if(key==='update'&&!u?.archived&&!u?.missing){
       throw new Error('倉位部分更新請使用交易');
      }
      const data=key==='delete'||key==='update'
       ?null
       :stockData(args[0].path,u);

      if(data)original.set(stockRef(db,args[0].path),data);
      else original.delete(stockRef(db,args[0].path));
     }
     return wrapped;
    };
   }
   const value=(target as any)[key];
   return typeof value==='function'?value.bind(target):value;
  }
 }) as WriteBatch;
 return wrapped;
}
