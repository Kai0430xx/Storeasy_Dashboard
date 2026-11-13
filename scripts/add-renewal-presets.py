from pathlib import Path

root = Path(__file__).resolve().parents[1]
updates = {}

def replace_checked(text, before, after, name):
    if before in text:
        return text.replace(before, after, 1)
    if after in text:
        return text
    raise SystemExit(f'{name} 版本不同，尚未修改檔案。請提供錯誤訊息。')

files = {
'src/renewal-presets.js': r'''import {validDate,taipeiDate} from './domain.js';
import {parseLease} from './lease.js';
export function renewalStart(unit){
 let end=unit?.leaseEnd;
 try{end=parseLease(unit?.leasePeriod||'').leaseEnd||end;}catch{}
 return validDate(end)?new Date(Date.parse(end+'T00:00:00Z')+86400000).toISOString().slice(0,10):taipeiDate();
}
export function renewalPeriod(start,months){
 if(!validDate(start)||start<'2000-01-01'||start>'2099-12-31'||![1,3,6,12].includes(months))throw Error('請選擇有效開始日期與租期。');
 const [year,month,day]=start.split('-').map(Number);
 const target=new Date(Date.UTC(year,month-1+months,1));
 const last=new Date(Date.UTC(target.getUTCFullYear(),target.getUTCMonth()+1,0)).getUTCDate();
 const end=new Date(Date.UTC(target.getUTCFullYear(),target.getUTCMonth(),Math.min(day,last))-86400000);
 const finish=end.toISOString().slice(0,10);
 if(finish>'2099-12-31')throw Error('租期不得超過2099年。');
 return `${start.replace(/-/g,'/')}－${finish.replace(/-/g,'/')}`;
}
''',
'src/RenewalLeaseField.tsx': r'''import {useState} from 'react';
import {renewalStart,renewalPeriod} from './renewal-presets.js';
import './renewal-presets.css';
type Row=Record<string,any>;
export default function RenewalLeaseField({unit,value,onChange,disabled=false,label='新的租期',ariaLabel=label,hint=''}:{unit:Row;value?:string;onChange?:(value:string)=>void;disabled?:boolean;label?:string;ariaLabel?:string;hint?:string}){
 const [manual,setManual]=useState(''),[start,setStart]=useState(()=>renewalStart(unit)),[months,setMonths]=useState<number|null>(null);
 const current=value===undefined?manual:value;
 const change=(next:string)=>onChange?onChange(next):setManual(next);
 let preview='',error='';
 if(months){try{preview=renewalPeriod(start,months);}catch(e){error=e instanceof Error?e.message:String(e);}}
 return <div className="renewal-lease-field">
  <fieldset className="renewal-presets" disabled={disabled}><legend>快速選擇租期</legend>
   <label>續約開始日<input aria-label={`${ariaLabel} 開始日`} type="date" value={start} onChange={e=>setStart(e.target.value)}/></label>
   <div className="renewal-preset-buttons">{([[1,'月租'],[3,'季租'],[6,'半年租'],[12,'年租']] as const).map(([n,text])=><button key={n} type="button" className={months===n?'primary':'secondary'} aria-pressed={months===n} onClick={()=>setMonths(n)}>{text}</button>)}</div>
   {months&&<div className="renewal-preview">{error?<p role="alert">{error}</p>:<><span>租期預覽</span><strong>{preview}</strong><button className="secondary" type="button" disabled={!preview||preview===current} onClick={()=>change(preview)}>{preview===current?'已套用':'確定套用'}</button></>}</div>}
   <small>預設接續原租期隔天；可修改開始日。預覽確認後才帶入下方。</small>
  </fieldset>
  <label>{label}<input aria-label={ariaLabel} name="leasePeriod" required disabled={disabled} value={current} onChange={e=>change(e.target.value)} placeholder="2026/10/08－2027/04/07" autoComplete="off"/><small>非1、3、6、12個月，可直接手動輸入完整起訖日期。</small>{hint&&<small>{hint}</small>}</label>
 </div>;
}
''',
'src/renewal-presets.css': r'''.renewal-lease-field{min-width:0}.renewal-presets{border:1px solid #dce5f1;border-radius:10px;padding:12px;margin:0 0 14px;min-width:0}.renewal-presets legend{padding:0 5px;font-weight:600}.renewal-presets label{margin:0 0 10px}.renewal-presets input{width:100%;min-width:0}.renewal-preset-buttons{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:10px 0}.renewal-preset-buttons button{min-height:40px;padding:8px 4px;white-space:nowrap}.renewal-preview{display:flex;align-items:center;flex-wrap:wrap;gap:8px;padding:10px 0}.renewal-preview>span{font-size:12px;color:#687c98}.renewal-preview>strong{font-variant-numeric:tabular-nums;overflow-wrap:anywhere}.renewal-preview button{min-height:38px;padding:8px 12px}.renewal-presets small,.renewal-lease-field>label>small{display:block;color:#687c98;line-height:1.6}.bulk-unit-fields>.renewal-lease-field{grid-column:1 / -1}@media(max-width:420px){.renewal-preset-buttons{gap:5px}.renewal-preview>strong{flex-basis:100%}}
''',
}

for name, content in files.items():
    path = root / name
    if path.exists() and path.read_text(encoding='utf-8') != content:
        raise SystemExit(f'{name} 已有不同內容，尚未覆蓋。')
    updates[path] = content

main_before = r'''{modal.type !== "exit" && (
                  <label>
                    {modal.type === "renew" ? "新的租期" : "租期"}
                    <input aria-label={modal.type === "renew" ? "新的租期" : "租期"} name="leasePeriod" required placeholder="2026/10/08－2027/04/07" autoComplete="off" />
                    <small className="hint">請貼上完整起訖日期，例如 2026/10/08－2027/04/07。</small>
                  </label>
                )}'''

main_after = r'''{modal.type !== "exit" && (
                  modal.type === "renew" ? <RenewalLeaseField key={`${modal.unit.branchId}/${modal.unit.code}`} unit={modal.unit} disabled={busy}/> :
                  <label>租期<input aria-label="租期" name="leasePeriod" required placeholder="2026/10/08－2027/04/07" autoComplete="off"/><small className="hint">請貼上完整起訖日期，例如 2026/10/08－2027/04/07。</small></label>
                )}'''

bulk_before = r'''        <label>新租期
         <input aria-label={`${row.unit.code} 新租期`}
          placeholder="2026/10/25－2027/01/24" value={row.leasePeriod}
          onChange={e=>patch(row.operationId,{leasePeriod:e.target.value})}
         /><small>{term}</small>
        </label>
'''

bulk_after = r'''        <RenewalLeaseField unit={row.unit} value={row.leasePeriod} onChange={leasePeriod=>patch(row.operationId,{leasePeriod})} disabled={locked} label="新租期" ariaLabel={`${row.unit.code} 新租期`} hint={term}/>
'''

for name, before, after in [
    ('src/main.tsx', main_before, main_after),
    ('src/BulkUnits.tsx', bulk_before, bulk_after),
]:
    path = root / name
    text = replace_checked(
        path.read_text(encoding='utf-8'),
        before,
        after,
        name
    )
    statement = "import RenewalLeaseField from './RenewalLeaseField';"
    if statement not in text:
        text = statement + '\n' + text
    updates[path] = text

path = root / 'src/manual-content.ts'
text = path.read_text(encoding='utf-8')
if '// renewal-presets-v1-manual' not in text:
    text += r'''
// renewal-presets-v1-manual
manualPages.find(p=>p.id==='units')?.topics.push({title:'續約快速選擇月租、季租、半年租及年租',steps:['登記續約及批次續約的新租期上方可選月租1個月、季租3個月、半年租6個月、年租12個月。開始日預設原租期結束的隔天，可自行修改；原租期未提供時預設今天。','點選後先查看「租期預覽」，按「確定套用」才會填入下方租期；套用不會送出或儲存續約，仍須按原本的確認儲存或批次確認送出。','租期包含開始與結束日：1/2月租到2/1、季租到4/1、半年到7/1、年租到隔年1/1。若目標月份沒有對應日期，先取該月月底再往前一天，例如1/31月租到2/27，閏年到2/28。','不是1、3、6、12個月時，直接手動輸入下方完整租期即可。改開始日或按預設選項只會改預覽，不會覆蓋已輸入的租期，需再按確定套用。','已付款仍按實際收款日期計入續約月份；未付款仍列待收款，租期已開始時顯示收款逾期。選項不會改動收款日期、活動或付款狀態。'],result:'只協助填入租期；每次續約仍需重新選擇活動及確認付款狀態。'});
'''
updates[path] = text

changed = 0
for path, text in updates.items():
    if not path.exists() or path.read_text(encoding='utf-8') != text:
        path.write_text(text, encoding='utf-8')
        changed += 1

print(f'續約快速租期選項更新完成，共修改 {changed} 個檔案。')
print('月底依目標月份同日或月底，再減一天。本次不需部署 Firebase。')
