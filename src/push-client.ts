
import {
  getFunctions,connectFunctionsEmulator,httpsCallable
} from 'firebase/functions';
import {onAuthStateChanged} from 'firebase/auth';
import {auth} from './firebase';

export type PushDevice={
  uid:string;
  deviceId:string;
  binding:string;
};

const functions=getFunctions(undefined,'asia-east1');
if(import.meta.env.VITE_USE_EMULATORS==='true'){
  connectFunctionsEmulator(functions,'127.0.0.1',5001);
}

const base=new URL(import.meta.env.BASE_URL,window.location.href);
const deviceKey='storeasy-push-device:'+base.pathname;
const ownerKey='storeasy-push-owner:'+base.pathname;

export const pushSupported=()=>
  ('Notification'in window)&&
  ('PushManager'in window)&&
  ('serviceWorker'in navigator);

export const iosDevice=()=>
  /iPhone|iPad|iPod/.test(navigator.userAgent)||
  (/Macintosh/.test(navigator.userAgent)&&navigator.maxTouchPoints>1);

export const standalone=()=>
  window.matchMedia('(display-mode: standalone)').matches||
  Boolean((navigator as any).standalone);

export function currentDevice():PushDevice|null{
  try{
    return JSON.parse(localStorage.getItem(deviceKey)||'null');
  }catch{
    return null;
  }
}

function installationKey(){
  let key=localStorage.getItem(ownerKey);
  if(!key){
    key=crypto.randomUUID()+crypto.randomUUID();
    localStorage.setItem(ownerKey,key);
  }
  return key;
}

export async function pushWorker(){
  if(!pushSupported()){
    throw new Error('這個瀏覽器尚不支援背景通知');
  }
  const registration=await navigator.serviceWorker.register(
    new URL('sw.js',base),{scope:base.pathname}
  );
  await navigator.serviceWorker.ready;
  return registration;
}

export async function workerMessage(type:string,value?:unknown){
  const registration=await pushWorker();
  const worker=registration.active;
  if(!worker){
    throw new Error('通知服務尚未準備好，請稍後重試');
  }

  await new Promise<void>((resolve,reject)=>{
    const channel=new MessageChannel();
    const timer=window.setTimeout(
      ()=>reject(new Error('通知服務回應逾時')),10000
    );
    channel.port1.onmessage=e=>{
      clearTimeout(timer);
      channel.port1.close();
      e.data?.ok
        ? resolve()
        : reject(new Error('裝置通知設定失敗'));
    };
    worker.postMessage({type,value},[channel.port2]);
  });
}

const rpc=async(name:string,data:unknown)=>
  ((await httpsCallable(functions,name)(data)).data as any);

export function notificationError(error:any){
  const code=String(error?.code||'');
  if(code.includes('not-found')||
     code.includes('unavailable')||
     code.includes('internal')){
    return '背景通知服務尚未就緒，請確認 Cloud Functions 與最新 Firebase 規則已部署。';
  }
  return error?.message||'通知設定失敗，請稍後重試';
}

export async function enablePush(){
  if(!pushSupported()){
    throw new Error('這個瀏覽器尚不支援背景通知');
  }
  if(iosDevice()&&!standalone()){
    throw new Error(
      'iPhone 請先用 Safari 加入主畫面，再從桌面圖示開啟並啟用通知'
    );
  }

  const uid=auth.currentUser?.uid;
  if(!uid)throw new Error('請先登入');

  const permission=await Notification.requestPermission();
  if(permission!=='granted'){
    throw new Error('尚未允許通知，請在手機或瀏覽器設定開啟');
  }

  const [registration,config]=await Promise.all([
    pushWorker(),rpc('pushConfig',{})
  ]);

  const configured=new URL(config.appUrl);
  if(import.meta.env.VITE_USE_EMULATORS!=='true'&&(
    configured.origin!==base.origin||
    configured.pathname!==base.pathname
  )){
    throw new Error(
      '推播服務的 PUSH_APP_URL 與目前網站不同，請主管確認部署設定'
    );
  }

  const raw=String(config.publicKey).replace(/-/g,'+').replace(/_/g,'/');
  const bytes=Uint8Array.from(
    atob(raw.padEnd(Math.ceil(raw.length/4)*4,'=')),
    c=>c.charCodeAt(0)
  );

  const subscription=
    (await registration.pushManager.getSubscription())||
    await registration.pushManager.subscribe({
      userVisibleOnly:true,
      applicationServerKey:bytes
    });

  const value=await rpc('pushSubscribe',{
    subscription:subscription.toJSON(),
    installationKey:installationKey()
  }) as PushDevice;

  if(auth.currentUser?.uid!==uid){
    await subscription.unsubscribe();
    throw new Error('帳號已變更，請重新啟用通知');
  }

  await workerMessage('bind',value);
  localStorage.setItem(deviceKey,JSON.stringify(value));
  return value;
}

export async function disableLocalPush(){
  localStorage.removeItem(deviceKey);
  if(!('serviceWorker'in navigator))return;

  const registration=await navigator.serviceWorker.getRegistration(
    base.href
  );
  if(!registration)return;

  try{await workerMessage('unbind');}catch{}
  try{
    await (await registration.pushManager.getSubscription())?.unsubscribe();
  }catch{}
  try{await (navigator as any).clearAppBadge?.();}catch{}
}

export async function disablePush(){
  const device=currentDevice(),uid=auth.currentUser?.uid;
  await disableLocalPush();

  if(device&&uid===device.uid){
    await Promise.race([
      rpc('pushUnsubscribe',{
        deviceId:device.deviceId,
        installationKey:installationKey()
      }),
      new Promise((_,reject)=>setTimeout(
        ()=>reject(new Error(
          '裝置已停用；伺服器連線逾時，失效訂閱將在後續推播自動清除'
        )),5000
      ))
    ]);
  }
}

export async function logoutNotifications(){
  try{await disablePush();}catch{}
}

onAuthStateChanged(auth,user=>{
  const device=currentDevice();
  if(device&&device.uid!==user?.uid){
    void disableLocalPush().catch(()=>{});
  }
});

export const saveOwnNotificationBranches=(branchIds:string[])=>rpc('pushOwnBranches',{branchIds});
