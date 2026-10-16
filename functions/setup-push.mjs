
import webpush from 'web-push';
import {execFileSync,spawnSync} from 'node:child_process';
import {
  mkdtempSync,writeFileSync,readFileSync,existsSync,rmSync
} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';

const project=process.argv[2]||'storeasy-dashboard';
if(!/^[a-z][a-z0-9-]{4,61}[a-z0-9]$/.test(project)){
  throw new Error('專案 ID 不正確');
}

const url=new URL(
  process.argv[3]||
  'https://kai0430xx.github.io/Storeasy_Dashboard/'
);

if(url.protocol!=='https:'||url.search||url.hash){
  throw new Error('請填網站的 HTTPS 根網址');
}
if(!url.pathname.endsWith('/'))url.pathname+='/';

const name='STOREASY_WEB_PUSH_VAPID';
const result=spawnSync('gcloud',[
  'secrets','describe',name,
  '--project',project,'--format=value(name)'
],{encoding:'utf8'});

if(result.status!==0){
  if(!/NOT_FOUND|not found|does not exist/i.test(
    (result.stderr||'')+(result.stdout||'')
  )){
    throw new Error(
      '無法查詢推播金鑰；請先登入 gcloud、選擇正確專案並啟用 Secret Manager API。'
    );
  }

  const folder=mkdtempSync(join(tmpdir(),'storeasy-vapid-'));
  try{
    const file=join(folder,'key.json');
    writeFileSync(file,JSON.stringify(webpush.generateVAPIDKeys()),{
      mode:0o600
    });
    execFileSync('gcloud',[
      'secrets','create',name,
      '--project',project,
      '--replication-policy=automatic',
      '--data-file',file
    ],{stdio:['ignore','ignore','pipe']});
    console.log('推播金鑰已建立。私鑰不會顯示。');
  }finally{
    rmSync(folder,{recursive:true,force:true});
  }
}else{
  console.log('沿用既有推播金鑰，未重新產生。');
}

const file=resolve('functions','.env.'+project);
let text=existsSync(file)?readFileSync(file,'utf8'):'';
const line='PUSH_APP_URL='+JSON.stringify(url.href);
text=/^PUSH_APP_URL=.*$/m.test(text)
  ? text.replace(/^PUSH_APP_URL=.*$/m,line)
  : text+'\n'+line+'\n';

writeFileSync(file,text,{mode:0o600});
console.log('網站網址已設定。接著部署 notifications Cloud Functions。');
