
/* No page caching: normal website updates remain fresh. */
const stateCache='storeasy-push-state:'+self.registration.scope;
const stateURL=new URL('__push_state__',self.registration.scope).href;
const tag='storeasy-unread:'+new URL(self.registration.scope).pathname;
let chain=Promise.resolve();

async function readState(){
  const response=await(await caches.open(stateCache)).match(stateURL);
  return response?response.json():null;
}

async function writeState(value){
  await(await caches.open(stateCache)).put(
    stateURL,
    new Response(JSON.stringify(value),{
      headers:{'Content-Type':'application/json'}
    })
  );
}

async function badge(count){
  try{
    if(count>0&&self.navigator.setAppBadge){
      await self.navigator.setAppBadge(count);
    }else if(self.navigator.clearAppBadge){
      await self.navigator.clearAppBadge();
    }
  }catch{}
}

function serial(fn){
  chain=chain.catch(()=>{}).then(fn);
  return chain;
}

self.addEventListener('install',event=>
  event.waitUntil(self.skipWaiting())
);
self.addEventListener('activate',event=>
  event.waitUntil(self.clients.claim())
);

self.addEventListener('message',event=>{
  const source=event.source?.url;
  if(!source||!source.startsWith(self.registration.scope))return;

  event.waitUntil(serial(async()=>{
    const data=event.data||{},old=await readState();

    if(data.type==='bind'){
      const v=data.value;
      if(!v||typeof v.uid!=='string'||
         typeof v.deviceId!=='string'||
         typeof v.binding!=='string'){
        throw new Error('Invalid device binding');
      }
      await writeState({...v,enabled:true,version:0,count:0});
      await badge(0);
    }else if(data.type==='unbind'){
      await writeState({enabled:false});
      await badge(0);
      for(const notification of
          await self.registration.getNotifications({tag})){
        notification.close();
      }
    }else if(data.type==='badge'){
      const v=data.value;
      if(old?.enabled&&v?.uid===old.uid&&
         v?.deviceId===old.deviceId&&v?.binding===old.binding&&
         Number.isInteger(v.count)&&v.count>=0&&
         v.version>=old.version){
        await writeState({...old,version:v.version,count:v.count});
        await badge(v.count);
      }
    }

    event.ports?.[0]?.postMessage({ok:true});
  }).catch(()=>event.ports?.[0]?.postMessage({ok:false})));
});

self.addEventListener('push',event=>
  event.waitUntil(serial(async()=>{
    let incoming;
    try{incoming=event.data?.json();}catch{return;}

    const old=await readState();
    if(!old?.enabled||!incoming||
       incoming.uid!==old.uid||
       incoming.deviceId!==old.deviceId||
       incoming.binding!==old.binding||
       !Number.isInteger(incoming.count)||incoming.count<0||
       !Number.isInteger(incoming.version))return;

    const value=incoming.version>=old.version
      ? {...old,...incoming}
      : old;

    await writeState(value);
    await badge(value.count);

    const target=new URL(self.registration.scope);
    target.hash=value.count
      ? (value.page==='waiting'?'waiting':'work')
      : 'dashboard';

    await self.registration.showNotification(
      value.count?'收多易・未讀提醒':'收多易・提醒已更新',
      {
        body:value.count
          ? '你有 '+value.count+' 筆未讀提醒。'
          : '目前沒有未讀提醒。',
        tag,
        renotify:false,
        silent:incoming.version<=old.version||
          value.count<old.count||value.count===0,
        icon:new URL(
          'icons/storeasy-icon.png?v=6adf06f11936',self.registration.scope
        ).href,
        data:{
          url:target.href,
          uid:value.uid,
          binding:value.binding
        }
      }
    );
  }))
);

self.addEventListener('notificationclick',event=>{
  event.notification.close();
  event.waitUntil(serial(async()=>{
    const state=await readState();
    const data=event.notification.data||{};

    if(!state?.enabled||state.uid!==data.uid||
       state.binding!==data.binding)return;

    const target=new URL(data.url||self.registration.scope);
    if(target.origin!==new URL(self.registration.scope).origin||
       !target.href.startsWith(self.registration.scope))return;

    const windows=await self.clients.matchAll({
      type:'window',includeUncontrolled:true
    });
    const existing=windows.find(client=>
      client.url.startsWith(self.registration.scope)
    );

    if(existing){
      await existing.navigate(target.href);
      await existing.focus();
    }else{
      await self.clients.openWindow(target.href);
    }
  }));
});

self.addEventListener('pushsubscriptionchange',event=>
  event.waitUntil(serial(async()=>{
    const state=await readState();
    if(!state?.enabled)return;
    await self.registration.showNotification(
      '收多易・通知連線已變更',
      {
        body:'請開啟網頁的通知設定，重新啟用此裝置通知。',
        tag,
        icon:new URL(
          'icons/storeasy-icon.png?v=6adf06f11936',self.registration.scope
        ).href,
        data:{
          url:self.registration.scope,
          uid:state.uid,
          binding:state.binding
        }
      }
    );
  }))
);
