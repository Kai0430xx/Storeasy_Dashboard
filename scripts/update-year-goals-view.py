from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = {}
marker = 'storeasy-year-goals-view-v1'

def replace(s, old, new, count=1):
    if s.count(old) != count:
        raise RuntimeError('版本不符，尚未寫入檔案：' + old[:70])
    return s.replace(old, new, 1)

name = 'src/GoalsOverview.tsx'
s = (root / name).read_text(encoding='utf-8')
if marker not in s:
    s = "import YearGoalsView from './YearGoalsView';\n" + s
    s = replace(
        s,
        '年度目標與轉介 Excel</button>{global&&',
        '年度目標與轉介 Excel</button><YearGoalsView branches={branches} records={records} data={data} year={year}/>{global&&'
    )
    s = replace(s, '<th>本月實際數值</th>', '')
    s = replace(s, '<td><MonthlyEntry branch={b} month={month} /></td>', '')
    s = replace(
        s,
        '{global&&onEdit&&<th>設定</th>}',
        '<th>設定</th>',
        2
    )
    s = replace(
        s,
        "{global&&onEdit&&<td><button className=\"text-button\" onClick={()=>onEdit({kind:'goal',branch:b,period:month,values:g||{}})}>設定月目標</button></td>}",
        "<td>{global&&onEdit&&<button className=\"text-button\" onClick={()=>onEdit({kind:'goal',branch:b,period:month,values:g||{}})}>設定月目標</button>}<MonthlyEntry branch={b} month={month}/></td>"
    )
    files[name] = s + '\n// ' + marker + '\n'

for name in ['src/MonthlyEntry.tsx', 'src/Targets.tsx']:
    s = (root / name).read_text(encoding='utf-8')
    files[name] = s.replace('輸入／修正本月數值', '設定實際數值')

component = r'''import {useEffect,useRef,useState} from 'react';
import {annualExportRows} from './annual-export';
import {taipeiDate} from './domain.js';
type Row=Record<string,any>;
const percent=(n:any)=>n==null?'未填':`${Number(n).toFixed(2)}%`;
export default function YearGoalsView({branches,records,data,year}:{branches:Row[];records:Row;data:Row;year:string}){
 const [open,setOpen]=useState(false),[selected,setSelected]=useState('');
 const modal=useRef<HTMLElement>(null);
 useEffect(()=>{setOpen(false);setSelected('');},[year,branches.map(b=>b.id).join(',')]);
 useEffect(()=>{
  if(!open)return;
  const previous=document.activeElement as HTMLElement|null;
  modal.current?.querySelector<HTMLButtonElement>('button')?.focus();
  const key=(e:KeyboardEvent)=>{
   if(e.key==='Escape'){e.preventDefault();setOpen(false);}
   if(e.key==='Tab'){
    const nodes=Array.from(modal.current?.querySelectorAll<HTMLElement>('button:not(:disabled),select:not(:disabled),[tabindex="0"]')||[]);
    const first=nodes[0],last=nodes.at(-1);
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}
    else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}
   }
  };
  document.addEventListener('keydown',key);
  return()=>{document.removeEventListener('keydown',key);if(previous?.isConnected)previous.focus();};
 },[open]);
 const branch=branches.find(b=>b.id===selected),record=branch?records[branch.id]:null;
 const ready=branch&&['targets','referrals','actuals'].every(k=>Array.isArray(record?.[k]))&&Array.isArray(data[branch.id]?.months);
 const rows=ready?annualExportRows([branch],{[branch.id]:{...record,months:data[branch.id].months}},year,taipeiDate()):[];
 function items(r:Row){
  const list:Row[]=[];
  if(r.occupancyTarget!=null)list.push({name:`出租率：${percent(r.occupancyTarget)}`,actual:percent(r.occupancy),result:r.occupancyResult});
  if(r.performanceTarget!=null)list.push({name:`業績完成率：${percent(r.performanceTarget)}`,actual:percent(r.performance),result:r.performanceResult});
  if(r.referralTarget!=null)list.push({name:`轉介數量：${r.referralTarget}`,actual:r.referrals??'未填',result:r.referralResult});
  for(const g of r.other||[])list.push({name:`${g.name}：${g.target}`,actual:g.actual??'未填',result:g.result});
  return list.length?list:[{name:'本月未設定目標',actual:'—',result:'未設定'}];
 }
 const status=(text:string)=>text==='達標'?<strong className="goal-achieved">達標</strong>:text;
 return <>
  <button disabled={!branches.length} onClick={()=>{setSelected(branches.length===1?branches[0].id:'');setOpen(true);}}>查看該據點當年度目標一覽</button>
  {open&&<div className="modal-backdrop" onClick={e=>{if(e.target===e.currentTarget)setOpen(false);}}><section ref={modal} className="modal year-goals-modal" role="dialog" aria-modal="true" aria-label="據點當年度目標一覽">
   <div className="panel-heading"><h2>{branch?.name||'據點'}・{year} 年度目標一覽</h2><button aria-label="關閉年度目標一覽" onClick={()=>setOpen(false)}>×</button></div>
   {branches.length>1&&<label>選擇據點<select aria-label="年度目標一覽據點" value={selected} onChange={e=>setSelected(e.target.value)}><option value="">請選擇據點</option>{branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label>}
   <p>依 1～12 月列出各月設定的目標；數值採 KPI 或已儲存的手動修正。「其它」採手填成果。達標顯示紅字。</p>
   {!branch?<p>請選擇要查看的據點。</p>:!ready?<p role="status">載入年度資料中…</p>:<div className="table-wrap year-goals-table" tabIndex={0} aria-label="年度目標表格捲動區"><table aria-label="據點全年每月目標"><thead><tr><th>月份</th><th>目標內容</th><th>實際數值</th><th>是否達標</th><th>整體月結果</th></tr></thead><tbody>{rows.flatMap(r=>{const list=items(r);return list.map((item,i)=><tr key={`${r.month}-${i}`}>
    {i===0&&<th scope="rowgroup" rowSpan={list.length}>{year}年{Number(r.month.slice(5))}月</th>}<td>{item.name}</td><td>{item.actual}</td><td>{status(item.result)}</td>{i===0&&<td rowSpan={list.length}>{status(r.overall)}</td>}
   </tr>);})}</tbody></table></div>}
  </section></div>}
 </>;
}
'''
name = 'src/YearGoalsView.tsx'
p = root / name
if p.exists() and p.read_text(encoding='utf-8') != component:
    raise RuntimeError('請先核對現有檔案：' + name)
files[name] = component

css = r'''
.modal.year-goals-modal {
  width: min(1100px, calc(100vw - 32px));
  height: min(900px, 94dvh);
  max-height: 94dvh;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}
.year-goals-modal > .panel-heading,
.year-goals-modal > label,
.year-goals-modal > p {
  flex-shrink: 0;
  margin: 0;
}
.year-goals-table {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
.year-goals-table table {
  min-width: 650px;
  width: 100%;
}
.year-goals-table thead th {
  position: sticky;
  top: 0;
  background: #f5f7fa;
  z-index: 1;
}
.year-goals-table th[scope="rowgroup"] {
  vertical-align: top;
}
.year-goals-table td {
  white-space: normal;
}
.year-goals-modal .goal-achieved {
  color: #b91c1c;
  font-weight: 700;
}
@media (max-width: 600px) {
  .modal.year-goals-modal {
    padding: 14px;
    width: calc(100vw - 24px);
  }
}
'''
name = 'src/style.css'
s = (root / name).read_text(encoding='utf-8')
if marker not in s:
    files[name] = s + '\n/* ' + marker + ' */\n' + css

for name, content in files.items():
    (root / name).write_text(content, encoding='utf-8')
    print('已更新 ' + name)

print('完成：年度目標視窗及右側實際數值按鈕；無須修改 Firebase 規則。')
