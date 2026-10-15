from pathlib import Path
import re

if Path('src/manual-pending-renewal.ts').exists():
    print('未付款勾選功能已套用。')
    raise SystemExit(0)

changes = {}

def edit(name, pattern, replacement):
    text = changes.get(name, Path(name).read_text(encoding='utf-8'))
    text, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise SystemExit(f'版本不符：{name}，尚未寫入任何檔案。')
    changes[name] = text

edit(
    'src/main.tsx',
    r'(leasePeriod:\s*(\w+)\.get\("leasePeriod"\),)',
    r'\1 unpaid: \2.get("unpaid"),'
)

edit(
    'src/main.tsx',
    r'(\{modal\.type !== "exit" && \(\s*<fieldset>\s*<legend>使用活動)',
    r'''{modal.type === "renew" && <label className="check-label"><input type="checkbox" name="unpaid" />未付款<small className="hint">勾選後先更新租期，列入待收款；確認收款後才計入續約。</small></label>}\1'''
)

edit(
    'src/api.ts',
    r'case "recordEvent":\s*\{',
    'case "recordEvent": {\n'
    '      if(data.unpaid === "on")return registerUnpaidRenewal(data);'
)

changes['src/api.ts'] = (
    'import {registerUnpaidRenewal} from "./manual-pending-renewal";\n'
    + changes['src/api.ts']
)

edit(
    'src/pending-renewals.ts',
    r'activities\s*:\s*\[\s*\](?=\s*,\s*unitSnapshot\s*:\s*r\.unitSnapshot)',
    'activities:r.unitSnapshot.activities||[]'
)

edit(
    'firestore.rules',
    r"(e\.paymentConfirmation\s*&&\s*e\.type\s*==\s*'renew'"
    r"\s*&&\s*!e\.voided\s*&&\s*)e\.activities\s*==\s*\[\s*\]",
    r"\1e.activities==before.unitSnapshot.get('activities',[]) "
    r"&& e.activities is list && e.activities.size()<=30"
)

changes['src/manual-pending-renewal.ts'] = r'''
import {collection,doc,runTransaction,serverTimestamp} from 'firebase/firestore';
import {auth,db} from './firebase';
import {parseLease} from './lease.js';
import {validDate,taipeiDate} from './domain.js';
import {priceSnapshot} from './pricing.js';
import {pendingRecord,renewalKey} from './pending-renewals';

export async function registerUnpaidRenewal(data:any){
 const uid=auth.currentUser?.uid;
 if(!uid)throw new Error('請先登入');

 const date=String(data.date||'');
 const lease=parseLease(data.leasePeriod);

 if(
  data.type!=='renew'
  ||!validDate(date)
  ||date>taipeiDate()
  ||!lease.leasePeriod
 )throw new Error('請填寫正確的續約日期與新租期');

 if(
  !Array.isArray(data.activityIds||[])
  ||(data.activityIds||[]).length>30
 )throw new Error('活動選擇不合法');

 const b=doc(db,'branches',data.branchId);
 const u=doc(b,'units',data.code);
 const p=doc(
  b,'pendingRenewals',
  renewalKey({code:data.code,...lease})
 );

 await runTransaction(db,async tx=>{
  const [bs,us,ps]=await Promise.all([
   tx.get(b),tx.get(u),tx.get(p)
  ]);
  const unit=us.data();
  const branch=bs.data();

  if(!branch||!unit||branch.importing)
   throw new Error('據點或倉位不存在，或據點正在匯入');

  if(unit.status!=='rented'||unit.missing||unit.archived)
   throw new Error('倉位狀態已變更，請重新開啟續約');

  if(unit.lastEventDate&&date<unit.lastEventDate)
   throw new Error('日期不得早於該倉位上一筆異動');

  if(ps.exists())
   throw new Error('此租期已有收款追蹤紀錄，請至待收款清單確認');

  const activities=[];
  for(const id of [...new Set(data.activityIds||[])] as string[]){
   const a=await tx.get(doc(collection(b,'activities'),id));
   if(
    !a.exists()
    ||a.data().archived
    ||a.data().month!==date.slice(0,7)
   )throw new Error('活動不適用於此月份');

   activities.push({id,name:a.data().name});
  }

  const frozen={
   ...unit,...lease,
   price:priceSnapshot(unit,date).price
  };
  const pending=pendingRecord(frozen,date,uid,'手動續約');

  tx.set(p,{
   ...pending,
   unitSnapshot:{...pending.unitSnapshot,activities}
  });

  tx.update(u,{
   ...lease,
   lastEventDate:date,
   lastEventId:null,
   updatedAt:serverTimestamp()
  });

  tx.update(b,{
   revision:branch.revision+1,
   updatedAt:serverTimestamp()
  });
 });

 return {};
}
'''.lstrip()

for name, content in changes.items():
    path = Path(name)
    backup = path.with_name(path.name + '.before-unpaid-checkbox')
    if path.exists() and not backup.exists():
        backup.write_text(
            path.read_text(encoding='utf-8'),
            encoding='utf-8'
        )
    path.write_text(content, encoding='utf-8')

print('已新增續約未付款勾選框。請建置網站並發布更新後的 firestore.rules。')
