from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
updates = {}

def load(path):
    return updates[path] if path in updates else path.read_text(encoding='utf-8')

def save(path, text):
    updates[path] = text

required = {
    'src/CalendarPage.tsx': 'calendarWeekLayout',
    'src/CalendarEditor.tsx': 'function CalendarTime(',
    'functions/calendar-domain.js': 'export function eventInput(raw)',
    'functions/calendar-service.js': 'export function createCalendarService(db)',
}
for name, text in required.items():
    path = root / name
    if not path.exists() or text not in load(path):
        raise SystemExit(f'{name} 版本不同，尚未修改檔案。')

if '/* calendar-optional-end-v4 */' in load(root / 'src/calendar.css'):
    print('節日名稱及選填結束功能已套用。')
    raise SystemExit(0)

p=root/'functions/calendar-domain.js';s=load(p).replace("'endDate','startTime'","'endDate','endDateUnset','startTime'")
s=s.replace("const startDate=String(raw.startDate||''),endDate=String(raw.endDate||startDate),allDay=raw.allDay===true;", "const startDate=String(raw.startDate||''),endDateUnset=raw.endDateUnset===true||!raw.endDate,endDate=endDateUnset?startDate:String(raw.endDate),allDay=raw.allDay===true;")
s=s.replace("if(!allDay&&(!/^([01]\\d|2[0-3]):[0-5]\\d$/.test(startTime)||!/^([01]\\d|2[0-3]):[0-5]\\d$/.test(endTime)||startDate===endDate&&endTime<=startTime))throw Error('請填寫正確起訖時間，結束須晚於開始');", "if(!allDay&&(!/^([01]\\d|2[0-3]):[0-5]\\d$/.test(startTime)||endTime&&(!/^([01]\\d|2[0-3]):[0-5]\\d$/.test(endTime)||startDate===endDate&&endTime<=startTime)))throw Error('請填寫正確開始時間；若填結束時間，須晚於開始');")
s=s.replace('return {title,notes,startDate,endDate,startTime,endTime,allDay,','return {title,notes,startDate,endDate,endDateUnset,startTime,endTime,allDay,');save(p,s)

p=root/'functions/calendar-service.js';s=load(p).replace('JSON.stringify(e[k])===JSON.stringify(proposed[k])',"JSON.stringify(k==='endDateUnset'?!!e[k]:e[k])===JSON.stringify(proposed[k])").replace('[k,e[k]]',"[k,k==='endDateUnset'?!!e[k]:e[k]]");save(p,s)

p=root/'src/calendar-client.ts';s=load(p).replace("startDate:date,endDate:date,startTime:'09:00',endTime:'10:00'","startDate:date,endDate:'',endDateUnset:true,startTime:'09:00',endTime:''");save(p,s)

p=root/'src/CalendarEditor.tsx';s=load(p);a=s.index('function CalendarTime(');b=s.index('export default function CalendarEditor',a)
s=s[:a]+'''function CalendarTime({label,value,onChange,optional=false}:{label:string;value:string;onChange:(value:string)=>void;optional?:boolean}){
 const [hour='',minute='']=String(value||'').split(':');
 return <fieldset className="calendar-time"><legend>{label}{optional?'（選填）':''}</legend><div><select required={!optional} aria-label={label+'（時）'} value={hour} onChange={e=>onChange(e.target.value?e.target.value+':'+(minute||'00'):'')}>{optional&&<option value="">未設定</option>}{Array.from({length:24},(_,i)=>String(i).padStart(2,'0')).map(v=><option key={v} value={v}>{v} 時</option>)}</select><span aria-hidden="true">:</span><select required={!optional} aria-label={label+'（分）'} value={minute} onChange={e=>onChange(e.target.value?(hour||'09')+':'+e.target.value:'')}>{optional&&<option value="">未設定</option>}{Array.from({length:60},(_,i)=>String(i).padStart(2,'0')).map(v=><option key={v} value={v}>{v} 分</option>)}</select></div></fieldset>;
}
'''+s[b:]
s=s.replace('{...initial,viewerIds:',"{...initial,endDate:initial.endDateUnset?'':initial.endDate,viewerIds:")
s=s.replace("const field=(key:string,newValue:any)=>setValue(v=>({...v,[key]:newValue}));", "const field=(key:string,newValue:any)=>setValue(v=>({...v,[key]:newValue,...(key==='endDate'?{endDateUnset:!newValue}:{})}));")
s=s.replace('endDate:v.endDate<date?date:v.endDate','endDate:v.endDate&&v.endDate<date?date:v.endDate')
s=s.replace('<label>結束日期<input type="date" required', '<label>結束日期（選填）<input aria-label="結束日期" type="date"')
s=s.replace('<CalendarTime label="結束時間"', '<CalendarTime optional label="結束時間"')
s=s.replace("endDate:form.due||new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Taipei'}),startTime:'09:00',endTime:'10:00'", "endDate:'',endDateUnset:true,startTime:'09:00',endTime:''")
save(p,s)

p=root/'src/CalendarPage.tsx';s=load(p).replace("'endDate','startTime'","'endDate','endDateUnset','startTime'")
pos=s.index('const statuses:');s=s[:pos]+'''const eventWhen=(e:CalRow)=>`${e.startDate} ${e.allDay?'全天':e.startTime}${!e.endDateUnset||e.endTime?` ～ ${!e.endDateUnset?e.endDate+' ':''}${e.allDay?'':e.endTime||''}`:''}`;
const diffValue=(v:CalRow,k:string)=>k==='endDate'&&v.endDateUnset?'':v[k];
'''+s[pos:]
s=s.replace("endDate:plusDays(e.endDate,days)","endDate:e.endDateUnset?'':plusDays(e.endDate,days)")
s=s.replace("title={`${e.title} · ${e.startDate} ${e.allDay?'全天':e.startTime} ～ ${e.endDate} ${e.allDay?'':e.endTime}`}","title={`${e.title} · ${eventWhen(e)}`}")
s=s.replace("<dd>{selected.startDate} {selected.allDay?'全天':selected.startTime} ～ {selected.endDate} {selected.allDay?'':selected.endTime}</dd>","<dd>{eventWhen(selected)}</dd>")
s=s.replace("<button className={'calendar-date'+", "<div className=\"calendar-date-heading\"><button className={'calendar-date'+")
s=s.replace("{Number(date.slice(8))}</button>{layout.hidden", "{Number(date.slice(8))}</button>{calendarHoliday(date)&&<span className=\"calendar-holiday-name\" title={calendarHoliday(date)}>{calendarHoliday(date)}</span>}</div>{layout.hidden")
s=s.replace("keys.filter(k=>JSON.stringify(reviewing.before[k])!==JSON.stringify(reviewing.proposed[k]))", "keys.filter(k=>k!=='endDateUnset'&&JSON.stringify(diffValue(reviewing.before,k))!==JSON.stringify(diffValue(reviewing.proposed,k)))")
s=s.replace("String(reviewing.before[k]||'—')", "String(diffValue(reviewing.before,k)||'未設定')").replace("String(reviewing.proposed[k]||'—')", "String(diffValue(reviewing.proposed,k)||'未設定')")
save(p,s)

p=root/'src/calendar.css';s=load(p)+'''
/* calendar-optional-end-v4 */
.calendar-date-heading{display:flex;align-items:center;gap:3px;min-width:0;height:28px}.calendar-date-heading .calendar-date{flex:0 0 28px;margin:0}.calendar-holiday-name{display:block;min-width:0;flex:1;color:#c62828;font-size:11px;line-height:1.25;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
@media(max-width:760px){.calendar-date-heading{height:24px;gap:1px}.calendar-date-heading .calendar-date{flex-basis:20px;width:20px;height:24px;font-size:12px}.calendar-holiday-name{font-size:10px}}
''';save(p,s)

p=root/'src/manual-content.ts';s=load(p)+'''
// calendar-optional-end-v4-manual
manualPages.find(p=>p.id==='calendar')?.topics.push({title:'節日名稱與選填結束時間',steps:['國定假日及補假的日期旁會顯示名稱；名稱過長會省略，電腦移到名稱可看全文。手機仍可在日期旁辨識節日名稱。','新增行程時，開始日期必填；非全天行程的開始時間必填。結束日期、結束時間預設空白，有需要再填，也可在修改時清空。','未填結束日期時，行程只顯示在開始當日，不會延伸到未來每天。只填結束時間時視為同一天；若填起訖時間，同日結束時間須晚於開始。','已填結束日期可形成跨日色條；結束時間仍可留白。拖曳及待辦日期同步會保留未設定結束的狀態；原有行程的結束日期、時間不會被自動清掉。'],result:'只顯示已填寫的起訖資料；仍保留全天、分享、修改申請及待辦同步。'});
''';save(p,s)

# 保留上一版取消成功提示的調整。
notice_files = [
    'src/main.tsx',
    'src/CalendarPage.tsx',
    'src/WorkTasks.tsx',
    'src/Targets.tsx',
    'src/BranchCheers.tsx',
    'src/MonthlyEntry.tsx',
    'src/NotificationCenter.tsx',
    'src/OwnNotificationBranches.tsx',
]
pattern = re.compile(
    r'\{notice\s*&&\s*(?:\(\s*)?'
    r'<(p|div|small)\b[^>]*>[\s\S]*?</\1>\s*(?:\))?\}'
)

for name in notice_files:
    path = root / name
    if not path.exists():
        raise SystemExit(f'找不到 {name}，尚未修改檔案。')
    original = load(path)
    updated, count = pattern.subn('', original)
    if count > 1 or (count == 0 and re.search(r'\{notice\s*&&', original)):
        raise SystemExit(f'{name} 的格式不同，尚未修改檔案。請提供錯誤訊息。')
    updates[path] = updated

name = 'src/WaitingList.tsx'
path = root / name
original = load(path)
updated, count = re.subn(
    r'\{savedNotice\s*&&\s*!edit\s*&&\s*'
    r'<div\b[^>]*>[\s\S]*?</div>\}', '', original
)
if count > 1 or (count == 0 and '{savedNotice&&' in original):
    raise SystemExit(f'{name} 的格式不同，尚未修改檔案。')
updates[path] = updated

path = root / 'src/ActivitySupplement.tsx'
original = load(path)
updates[path] = original.replace(
    "setMessage('當月活動已補登')", "setMessage('')"
)

path = root / 'src/GoalsOverview.tsx'
original = load(path)
old = "setMessage(`成功 ${completed} 間${failed.length?`；失敗 ${failed.length} 間：${failed.join('；')}`:''}`)"
new = "setMessage(failed.length?`成功 ${completed} 間；失敗 ${failed.length} 間：${failed.join('；')}`:'')"
if old not in original and new not in original:
    raise SystemExit('GoalsOverview.tsx 的格式不同，尚未修改檔案。')
updated = original.replace(old, new).replace(
    'setMessage(`${year} 年度 Excel 已匯出`)', 'setMessage("")'
)
updates[path] = updated

path = root / 'src/manual-content.ts'
original = load(path)
marker = '// quiet-success-notices-v1-manual'
manual = '''
// quiet-success-notices-v1-manual
manualPages.find(p=>p.id==='dashboard')?.topics.push({
 title:'操作成功後不再顯示提示橫幅',
 steps:[
  '各頁面新增、儲存、修改、刪除、匯入或完成設定後，不再顯示需要手動關閉的成功提示。可直接在更新後的清單或資料確認結果。',
  '操作失敗、權限不足及填寫錯誤仍會顯示，請依訊息修正。處理中的進度、待確認畫面與批次成功／失敗／待處理筆數仍保留。',
  '此調整不影響鈴鐺未讀、日曆修改申請及手機背景推播；候補篩選條件提示與還原篩選按鈕也保留。'
 ],
 result:'不會自動關閉錯誤訊息，也不改變資料儲存、刪除或通知權限。'
});
'''
updates[path] = original if marker in original else original + manual

changed = 0
for path, updated in updates.items():
    if path.read_text(encoding='utf-8') != updated:
        path.write_text(updated, encoding='utf-8')
        changed += 1
print(f'節日名稱與選填結束功能更新完成，共修改 {changed} 個檔案。')
print('請接著部署 notifications Cloud Functions，讓結束可留白。')
