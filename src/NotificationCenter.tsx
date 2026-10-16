
import {useEffect,useState} from 'react';
import {doc,onSnapshot} from 'firebase/firestore';
import {Bell,X} from 'lucide-react';
import {db} from './firebase';
import {
  currentDevice,disablePush,enablePush,iosDevice,
  notificationError,pushSupported,standalone,workerMessage,
  PushDevice
} from './push-client';
import './notifications.css';

export default function NotificationCenter({
  uid,role
}:{uid:string;role:string}){
  const [open,setOpen]=useState(false);
  const [device,setDevice]=useState<PushDevice|null>(currentDevice);
  const [active,setActive]=useState(false);
  const [count,setCount]=useState<number|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const supported=pushSupported();
  const needsInstall=iosDevice()&&!standalone();

  useEffect(()=>{
    setActive(false);
    setCount(null);
    if(!device||device.uid!==uid)return;

    return onSnapshot(doc(db,'pushDevices',device.deviceId),s=>{
      setActive(
        s.exists()&&s.data().uid===uid&&
        s.data().binding===device.binding&&
        pushSupported()&&Notification.permission==='granted'
      );
    },()=>setActive(false));
  },[uid,device?.deviceId,device?.binding]);

  useEffect(()=>{
    setCount(null);
    if(!active||!device)return;

    return onSnapshot(doc(db,'pushStatus',uid),s=>{
      const value=s.data();
      if(!value)return;
      setCount(value.count);
      void workerMessage('badge',{
        ...device,version:value.version,count:value.count
      }).catch(()=>{});
    });
  },[uid,active,device?.binding]);

  async function enable(){
    if(busy)return;
    setBusy(true);setError('');setNotice('');
    try{
      const value=await enablePush();
      setDevice(value);
      setNotice('此裝置已啟用背景通知');
    }catch(e){
      setError(notificationError(e));
    }finally{
      setBusy(false);
    }
  }

  async function disable(){
    if(busy)return;
    setBusy(true);setError('');setNotice('');
    try{
      await disablePush();
      setNotice('此裝置通知已停用');
    }catch(e){
      setError(notificationError(e));
    }finally{
      setDevice(null);setActive(false);setCount(null);setBusy(false);
    }
  }

  return <>
    <button type="button" className="notification-settings-button"
      title="通知設定" aria-label="通知設定"
      onClick={()=>{
        setOpen(true);setError('');setNotice('');
      }}>
      <Bell size={18}/>
      {active&&count!==null&&count>0&&
        <span>{count>99?'99+':count}</span>}
    </button>

    {open&&<div className="modal-backdrop">
      <section className="modal notification-modal"
        role="dialog" aria-modal="true" aria-label="通知設定">
        <div className="modal-heading">
          <h2>通知設定</h2>
          <button type="button" aria-label="關閉"
            disabled={busy} onClick={()=>setOpen(false)}>
            <X size={20}/>
          </button>
        </div>

        <p>
          沒開網頁時，也能收到
          {role==='manager'?'待辦與所屬據點候補':'待辦'}提醒。
          桌面圖示數字依系統支援顯示，每筆只算一次。
        </p>
        <p className="hint">
          {role==='manager'
            ? '候補據點包含所屬分店才會提醒；待辦依可查看事項的未讀紅點。'
            : '只有明確指派給你的主事項或子項目會通知；能查看全部事項不代表會收到全部通知。'}
        </p>

        <p className="notification-state">
          此裝置：<strong>{active?'已啟用':'尚未啟用'}</strong>
          {active&&count!==null&&<span> · 未讀 {count} 筆</span>}
        </p>

        {needsInstall&&<div className="alert">
          iPhone 請先用 Safari 開啟網站，按分享 → 加入主畫面，
          再從桌面圖示開啟本網站並啟用通知。需 iOS 16.4 以上。
        </div>}

        {!supported&&!needsInstall&&<div className="alert">
          目前瀏覽器不支援背景通知，
          請改用支援的瀏覽器或加入主畫面後再試。
        </div>}

        {supported&&Notification.permission==='denied'&&
          <p className="hint">
            通知權限已關閉，請到手機或瀏覽器的通知設定重新允許。
          </p>}

        <p className="hint">
          通知只顯示未讀筆數，不放客人個資或訊息內容。
          系統可能因專注模式、網路或省電設定延遲；
          此設定只影響這個裝置。
        </p>

        {error&&<p role="alert" className="alert error">{error}</p>}
        {notice&&<p role="status" className="alert success">{notice}</p>}

        <div className="notification-actions">
          <button type="button" className="primary"
            disabled={busy||!supported||needsInstall}
            onClick={enable}>
            {busy?'處理中…':active
              ? '重新連線通知':'開啟此裝置通知'}
          </button>
          <button type="button" className="secondary"
            disabled={busy||!device||device.uid!==uid}
            onClick={disable}>
            停用此裝置通知
          </button>
        </div>
      </section>
    </div>}
  </>;
}
