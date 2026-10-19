from pathlib import Path
import re

r = Path(__file__).resolve().parents[1]
changes = {}

raw = r'''
import {parseUnits} from './imports.js';
const norm=v=>String(v??'').normalize('NFKC').trim();
const missing=v=>v==null||typeof v==='number'&&!Number.isFinite(v)||/^(?:|[+-]?(?:∞|infinity)|nan|n\/?a|無數值|无数值|無|无|#(?:DIV\/0!|VALUE!|N\/A|NUM!|REF!|NAME\?|NULL!)|[-—–])$/i.test(norm(v));

function cleanNumber(v,cell,fixes){
 if(missing(v)){
  if(v!==0)fixes.push({cell,before:String(v??'空白'),after:0});
  return 0;
 }
 const text=norm(v).replace(/NT\$|NTD|TWD|元|[$,\s]/gi,'');
 const n=Number(text);
 if(!text||!Number.isFinite(n)||n<0)throw Error(cell+' 數值不合法，請檢查原檔');
 return n;
}

function cleanDimensions(value,cell,fixes){
 const text=norm(value),num='\\d+(?:\\.\\d+)?';
 const part=`${num}\\s*[*xX×]\\s*${num}\\s*[*xX×]\\s*${num}`;
 const match=text.match(new RegExp(`^(${part}(?:\\s*[+-]\\s*${part})*)`));
 if(!match)throw Error(cell+' 尺寸格式無法辨識');
 const rest=text.slice(match[0].length).trim();
 if(rest&&!rest.split(/\s+/).every(v=>/^\d+(?:\.\d+)?$/.test(v))){
  throw Error(cell+' 尺寸後有無法辨識的文字');
 }
 if(rest)fixes.push({cell,before:text,after:match[1].trim()});
 return match[1].trim();
}

// raw-inventory-simple-v2
export function parseInventoryFile(book){
 const name=book.SheetNames[0],raw=book.Sheets[name];
 if(!raw?.length)throw Error('工作表沒有資料');
 const fixes=[];

 if(raw[0].some(v=>['倉位','倉位編號','倉號'].includes(norm(v)))){
  const headers=raw[0].map(v=>norm(v).replace(/\s/g,'').replace(/\((?:NT\$|NTD|元|新臺幣|新台幣)\)/gi,''));
  const numeric=['材積','材積數','單價','月租','月租金','月租金額','原價','月繳','金額'];
  const rows=raw.map((r,i)=>i===0?r:Array.from(
   {length:Math.max(raw[0].length,r.length)},
   (_,c)=>numeric.includes(headers[c])
    ?cleanNumber(r[c],`第 ${i+1} 列 ${headers[c]}`,fixes)
    :r[c]
  ));
  return {
   units:parseUnits({...book,Sheets:{...book.Sheets,[name]:rows}},name,{requirePrice:true,requireLease:true}),
   report:{format:'有標題倉位表',merged:0,fixes}
  };
 }

 const ignored=new Map();
 for(const range of book.Merges?.[name]||[]){
  const m=range.match(/^\$?B\$?(\d+):\$?B\$?(\d+)$/);
  if(m)for(let r=Number(m[1])+1;r<=Number(m[2]);r++)ignored.set(r,Number(m[1]));
 }

 const rows=[['倉位','尺寸','材積','單價','月租','租期']];
 let merged=0;
 for(let i=0;i<raw.length;i++){
  const r=raw[i];
  if(!r.some(v=>norm(v)))continue;
  if(norm(r[0])||!norm(r[1])||!norm(r[2])||r.slice(13).some(v=>norm(v))){
   throw Error(`第 ${i+1} 列不是支援的原始格式，請確認欄位`);
  }
  if(ignored.has(i+1)){
   const master=raw[ignored.get(i+1)-1];
   if([1,2,3,5,6,10].some(c=>norm(r[c])!==norm(master[c]))){
    throw Error(`第 ${i+1} 列合併倉位有不同資料`);
   }
   merged++;
   continue;
  }
  const code=norm(r[1]);
  if(!/\d/.test(code))throw Error(`第 ${i+1} 列倉號無法辨識`);
  rows.push([
   code,
   cleanDimensions(r[2],`C${i+1} (${code})`,fixes),
   cleanNumber(r[3],`D${i+1} (${code})`,fixes),
   cleanNumber(r[5],`F${i+1} (${code})`,fixes),
   cleanNumber(r[6],`G${i+1} (${code})`,fixes),
   r[10]
  ]);
 }
 return {
  units:parseUnits({SheetNames:[name],Sheets:{[name]:rows}},name,{requirePrice:true,requireLease:true}),
  report:{
   format:'系統原始下載檔',merged,fixes,
   ignored:'略過 A 欄、坪數 E 欄、季／半年／年繳 H～J 欄及租期後 L／M 欄；備註不影響倉位數與空倉判斷。'
  }
 };
}
'''

report = r'''
  {preview.report&&<div className="raw-import-report">
   <h3>原始檔辨識結果</h3>
   <p>{preview.report.format}；合併續列略過 {preview.report.merged} 列；自動整理 {preview.report.fixes.length} 格。</p>
   <p className="hint">{preview.report.ignored}</p>
   {preview.report.fixes.length>0&&<details>
    <summary>查看自動整理明細</summary>
    {preview.report.fixes.map((v:any,i:number)=><p key={i}>{v.cell}：{v.before} → {String(v.after)}</p>)}
   </details>}
  </div>}
'''

hook = r'''
 // waiting-bulk-read-v1
 async function markManyRead(targets:WaitingRow[]){
  if(!uid||!ready)throw Error('候補清單尚未載入完成');
  const jobs=[...new Map(targets.map(row=>[row.id,row])).values()]
   .filter(row=>!row.deleting&&unread(row))
   .map(row=>({
    id:row.id,
    keys:['created',...(matches[row.id]||[]).map(vacancyKey),...(isExpired(row)?[expiryKey(row)]:[])]
   }));
  let completed=0,failed=0;
  for(let i=0;i<jobs.length;i+=20){
   const results=await Promise.allSettled(jobs.slice(i,i+20).map(async job=>{
    const ref=doc(db,'waitingReads',uid,'items',job.id);
    await runTransaction(db,async tx=>{
     const old=await tx.get(ref);
     tx.set(ref,{seen:[...new Set([...(old.data()?.seen||[]),...job.keys])].slice(-2000)});
    });
   }));
   for(const result of results)result.status==='fulfilled'?completed++:failed++;
  }
  if(failed)throw Error(`已完成 ${completed} 筆，${failed} 筆未完成，請重試`);
  return completed;
 }
'''

ui = r'''
 // waiting-bulk-read-v1
 const selectable=list.filter(r=>!r.deleting);
 const picked=selectable.filter(r=>checked.includes(r.id));
 useEffect(()=>{
  const ids=new Set(selectable.map(r=>r.id));
  setChecked(old=>old.filter(id=>ids.has(id)));
 },[selectable.map(r=>r.id).join('|')]);

 async function readBatch(all:boolean){
  if(busy)return;
  setBusy(true);setError('');
  try{
   const count=await state.markManyRead(all?selectable:picked);
   setChecked([]);
   setSavedNotice(`已將 ${count} 筆候補設為已讀`);
  }catch(e:any){
   setError(e.message||'標記已讀失敗，請重試');
  }finally{setBusy(false);}
 }
'''

toolbar = r'''
  <div className="waiting-read-toolbar">
   <label><input type="checkbox" aria-label="全選目前候補"
    disabled={busy||!state.ready||!selectable.length}
    checked={!!selectable.length&&picked.length===selectable.length}
    ref={e=>{if(e)e.indeterminate=picked.length>0&&picked.length<selectable.length;}}
    onChange={e=>setChecked(e.target.checked?selectable.map(r=>r.id):[])}
   />全選目前清單</label>
   <span>已勾選 {picked.length} 筆</span>
   <button className="secondary" disabled={busy||!state.ready||!picked.some(state.unread)} onClick={()=>readBatch(false)}>勾選項目已讀</button>
   <button className="secondary" disabled={busy||!state.ready||!selectable.some(state.unread)} onClick={()=>readBatch(true)}>全部已讀</button>
   <small>僅套用目前據點、狀態及搜尋篩選後的清單。</small>
  </div>
'''

checkbox = r'''
<input className="waiting-read-check" type="checkbox"
 aria-label={'勾選候補 '+r.name}
 disabled={busy||!state.ready||!!r.deleting}
 checked={checked.includes(r.id)}
 onChange={e=>setChecked(old=>e.target.checked?[...old,r.id]:old.filter(id=>id!==r.id))}
/>'''

css = r'''
/* waiting-bulk-read-v1 */
.waiting-read-toolbar{display:flex;align-items:center;flex-wrap:wrap;gap:12px;margin:14px 0;font-size:13px}
.waiting-read-toolbar label{display:flex;flex-direction:row;align-items:center;gap:8px;margin:0}
.waiting-read-toolbar small{width:100%;color:#7c899b}
.waiting-read-toolbar input,.waiting-read-check{width:18px;height:18px;flex-shrink:0;vertical-align:middle}
.waiting-read-check{margin:0 8px 0 0}
@media(max-width:760px){.waiting-read-toolbar button{min-height:44px}.waiting-read-check{width:22px;height:22px}}
'''

manual = r'''
// inventory-waiting-simple-v2-manual
manualPages.find(p=>p.id==='imports')?.topics.push({title:'直接匯入原始倉位表，只抓月繳牌價',steps:['上傳系統下載的原始 .xlsx，不需刪 A 欄或補標題。讀取 B 倉號、C 尺寸、D 材積、F 單價、G 月繳及 K 租期；其餘欄位與備註忽略，不處理年繳折扣。','合併的同一倉位只計算一次；尺寸後誤接的純數字會移除，材積與月租仍取原本獨立欄位，不依尺寸推算。','數值欄位的無限符號、Infinity、無數值、NaN、空白及 Excel 數值錯誤轉為 0；其他無法辨識文字會停止分析。租期空白代表空倉，備註不影響判斷。','查看總倉、已出租、空倉與自動整理明細，確認後才匯入。傳統有標題的倉位表仍可使用。'],result:'分析不寫入資料；確認匯入沿用原先全部覆蓋或差異匯入流程。只抓月繳牌價，不加入季繳／半年繳／年繳價格。'});
manualPages.find(p=>p.id==='waiting')?.topics.push({title:'勾選已讀與全部已讀',steps:['候補姓名旁可勾選，或按「全選目前清單」，再按「勾選項目已讀」。','「全部已讀」只處理目前據點、狀態、搜尋及空倉配對篩選後的清單，包含紅色到期與黃色配對提醒。','僅更新自己帳號的已讀狀態，同帳號其它裝置會同步；其他帳號不受影響。新配對或到期日期變更仍會產生新提醒。'],result:'不刪除候補、不改客戶狀態。讀取尚未完成時不可操作；失敗會顯示訊息，已成功項目保留，未完成可重試。'});
'''

changes[r / 'src/raw-inventory.js'] = raw

p = r / 'src/imports.js'
s = p.read_text()
if 'result.Merges[sheet.name]' not in s:
    anchor = 'result.SheetNames.push(sheet.name);'
    assert anchor in s
    s = s.replace(
        anchor,
        anchor + '\n    result.Merges ||= {};\n'
        '    result.Merges[sheet.name] = sheet.model.merges || [];'
    )
changes[p] = s

p = r / 'src/InventoryReview.tsx'
s = p.read_text()
if 'raw-import-report' in s:
    a = s.index('{preview.report&&')
    b = s.index('<h3>與既有資料不同的倉位</h3>', a)
    s = s[:a] + s[b:]
if '<label>原始檔年繳金額' in s:
    a = s.index('<label>原始檔年繳金額')
    b = s.index('<label>盤點／新價格生效日期', a)
    s = s[:a] + s[b:]

if 'parseInventoryFile' in s:
    a = s.index("const {workbook}=await import('./imports');")
else:
    a = s.index("const {workbook,parseUnits}=await import('./imports');")
b = s.index('const comparison=compareInventory', a)
s = s[:a] + """const {workbook}=await import('./imports');
 const {parseInventoryFile}=await import('./raw-inventory.js');
 const file=f.get('all') as File;
 const {units:rows,report}=parseInventoryFile(await workbook(await file.arrayBuffer()));
 """ + s[b:]
s = s.replace(
    'filename:file.name});',
    'filename:file.name,report});'
)
anchor = '<h3>與既有資料不同的倉位</h3>'
assert anchor in s
s = s.replace(anchor, report + anchor)
changes[p] = s

p = r / 'src/waiting-list.ts'
s = p.read_text()
if '// waiting-bulk-read-v1' not in s:
    anchor = ' return {rows,stock:availableStock'
    assert anchor in s
    s = s.replace(anchor, hook + anchor).replace(
        'hasUnread:rows.some(unread),markRead,ready',
        'hasUnread:rows.some(unread),markRead,markManyRead,ready'
    )
changes[p] = s

p = r / 'src/WaitingList.tsx'
s = p.read_text()
if '// waiting-bulk-read-v1' not in s:
    anchor = " const [savedNotice,setSavedNotice]=useState('');"
    assert anchor in s
    s = s.replace(
        anchor,
        anchor + "\n const [checked,setChecked]=useState<string[]>([]);"
    )
    anchor = ' const startEdit='
    assert anchor in s
    s = s.replace(anchor, ui + anchor)
    anchor = '  <section className="panel waiting-summary">'
    assert anchor in s
    s = s.replace(anchor, toolbar + anchor)
    anchor = '<td data-label="姓名">'
    assert anchor in s
    s = s.replace(anchor, anchor + checkbox)
changes[p] = s

p = r / 'src/waiting-list.css'
s = p.read_text()
if '/* waiting-bulk-read-v1 */' not in s:
    s += '\n' + css
changes[p] = s

p = r / 'src/manual-content.ts'
s = p.read_text()
s = re.sub(r'// raw-inventory-v1-manual\n[^\n]*\n?', '', s)
if '// inventory-waiting-simple-v2-manual' not in s:
    s += '\n' + manual
changes[p] = s

for p, s in changes.items():
    p.write_text(s, encoding='utf-8')

print('已加入簡化原始檔匯入與候補勾選／全部已讀。')
