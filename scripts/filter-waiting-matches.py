from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
changes = {}

component = """
import {useState} from 'react';

type Row=Record<string,any>;

export default function WaitingMatches({
 active,units,branchIds,names
}:{
 active:boolean;
 units:Row[];
 branchIds:string[];
 names:Map<string,any>;
}){
 const [chosen,setChosen]=useState<string[]|null>(null);
 const [low,setLow]=useState('');
 const [high,setHigh]=useState('');
 const [sort,setSort]=useState('default');

 const ids=[...new Set([
  ...branchIds,
  ...units.map(u=>u.branchId)
 ])];

 const selected=chosen===null?ids:chosen;

 const invalid=
  (low!==''&&(!Number.isFinite(Number(low))||Number(low)<0))||
  (high!==''&&(!Number.isFinite(Number(high))||Number(high)<0))||
  (low!==''&&high!==''&&Number(low)>Number(high));

 const compare=(a:Row,b:Row)=>
  String(names.get(a.branchId)||a.branchId).localeCompare(
   String(names.get(b.branchId)||b.branchId),'zh-TW'
  )||
  String(a.code).localeCompare(
   String(b.code),'zh-TW',{numeric:true}
  );

 const rows=invalid?[]:units.filter(u=>
  selected.includes(u.branchId)&&
  (low===''||u.volume>=Number(low))&&
  (high===''||u.volume<=Number(high))
 ).sort((a,b)=>
  (sort==='asc'?a.price-b.price:
   sort==='desc'?b.price-a.price:0)||compare(a,b)
 );

 function toggle(id:string,checked:boolean){
  setChosen(
   checked?[...new Set([...selected,id])]:
   selected.filter(x=>x!==id)
  );
 }

 function reset(){
  setChosen(null);
  setLow('');
  setHigh('');
  setSort('default');
 }

 return (
  <section className="waiting-matches" aria-label="合適空倉">
   <h3>合適空倉</h3>
   {!active?<p>這筆紀錄已停止配對。</p>:<>
    <p className="hint">
     依材積與月租範圍比對；需求時間供店長確認，不保證預留至該日期。
    </p>

    <div className="waiting-match-filters">
     <div>
      <span className="waiting-match-label">據點（可複選）</span>
      <details className="waiting-match-branches">
       <summary>
        {selected.length===ids.length?
         '全部候補據點':`已選 ${selected.length} 間據點`}
       </summary>
       <div>
        <label>
         <input
          type="checkbox"
          aria-label="全選配對據點"
          checked={ids.length>0&&ids.every(id=>selected.includes(id))}
          onChange={e=>setChosen(e.target.checked?null:[])}
         />
         全選
        </label>
        {ids.map(id=>
         <label key={id}>
          <input
           type="checkbox"
           aria-label={'配對據點 '+(names.get(id)||id)}
           checked={selected.includes(id)}
           onChange={e=>toggle(id,e.target.checked)}
          />
          <span>
           {names.get(id)||id}
           （{units.filter(u=>u.branchId===id).length}）
          </span>
         </label>
        )}
       </div>
      </details>
     </div>

     <div>
      <span className="waiting-match-label">材積範圍</span>
      <div className="waiting-match-range">
       <input
        aria-label="空倉材積下限"
        type="number"
        min="0"
        step="any"
        placeholder="下限"
        value={low}
        onChange={e=>setLow(e.target.value)}
       />
       <span>～</span>
       <input
        aria-label="空倉材積上限"
        type="number"
        min="0"
        step="any"
        placeholder="上限"
        value={high}
        onChange={e=>setHigh(e.target.value)}
       />
      </div>
     </div>

     <label>
      月租排序
      <select
       aria-label="空倉月租排序"
       value={sort}
       onChange={e=>setSort(e.target.value)}
      >
       <option value="default">依據點／倉號</option>
       <option value="asc">價格低到高</option>
       <option value="desc">價格高到低</option>
      </select>
     </label>
    </div>

    <div className="waiting-match-result">
     <span role="status">
      顯示 {rows.length}／{units.length} 間
     </span>
     <button
      type="button"
      className="text-button"
      onClick={reset}
     >
      清除篩選
     </button>
    </div>

    {invalid&&
     <p role="alert" className="alert error">
      材積請填非負數，下限不可大於上限。
     </p>
    }

    <div className="table-wrap">
     <table>
      <thead>
       <tr>
        <th>據點</th>
        <th>倉號</th>
        <th>材積</th>
        <th>月租</th>
       </tr>
      </thead>
      <tbody>
       {rows.map(u=>
        <tr key={u.branchId+'/'+u.code}>
         <td>{names.get(u.branchId)||u.branchId}</td>
         <td>{u.code}</td>
         <td>{u.volume}</td>
         <td>NT$ {u.price.toLocaleString('zh-TW')}</td>
        </tr>
       )}
      </tbody>
     </table>
    </div>

    {!invalid&&!rows.length&&
     <p>
      {units.length?
       '沒有符合目前篩選條件的空倉，可調整條件或清除篩選。':
       '目前沒有符合的空倉；其它據點僅記錄，不自動配對。'}
     </p>
    }
   </>}
  </section>
 );
}
"""

p = root / 'src/WaitingList.tsx'
s = p.read_text(encoding='utf-8')

if 'import WaitingMatches from' not in s:
    start = s.find('<h3>合適空倉</h3>')
    end = s.find('<div className="toolbar">', start)

    if start < 0 or end < 0:
        raise SystemExit('找不到合適空倉區塊，未更動檔案。')

    replacement = (
        '<WaitingMatches key={row.id} '
        'active={activeWaiting(row)} '
        'units={state.matches[row.id]||[]} '
        'branchIds={row.branchIds} names={names}/>\n   '
    )
    s = s[:start] + replacement + s[end:]
    s = 'import WaitingMatches from "./WaitingMatches";\n' + s

changes['src/WaitingList.tsx'] = s
changes['src/WaitingMatches.tsx'] = component

p = root / 'src/waiting-list.css'
s = p.read_text(encoding='utf-8')

if '/* waiting-match-filters-v1 */' not in s:
    s += """
/* waiting-match-filters-v1 */
.waiting-matches {
 min-width:0;
}
.waiting-match-filters {
 display:grid;
 grid-template-columns:1fr 1.2fr 1fr;
 gap:12px;
 align-items:start;
 margin:18px 0 10px;
}
.waiting-match-filters > * {
 min-width:0;
}
.waiting-match-label {
 display:block;
 font-size:14px;
 font-weight:500;
 margin-bottom:8px;
}
.waiting-match-branches {
 border:1px solid #dae3ed;
 border-radius:8px;
 background:#fff;
}
.waiting-match-branches summary {
 cursor:pointer;
 padding:12px;
}
.waiting-match-branches > div {
 max-height:210px;
 overflow:auto;
 padding:0 10px 10px;
}
.waiting-match-branches label {
 display:flex!important;
 flex-direction:row!important;
 align-items:center;
 gap:8px;
 padding:8px 0;
 margin:0;
}
.waiting-match-branches input {
 width:18px!important;
 height:18px;
 flex:0 0 18px;
}
.waiting-match-branches span {
 overflow-wrap:anywhere;
}
.waiting-match-range {
 display:flex;
 align-items:center;
 gap:6px;
}
.waiting-match-range input {
 min-width:0;
 width:100%;
}
.waiting-match-result {
 display:flex;
 align-items:center;
 justify-content:space-between;
 gap:12px;
 margin:12px 0;
 color:#718099;
 font-size:13px;
}
@media(max-width:600px){
 .waiting-match-filters {
  grid-template-columns:1fr;
 }
}
"""

changes['src/waiting-list.css'] = s

p = root / 'src/manual-waiting.ts'
s = p.read_text(encoding='utf-8')

if '合適空倉的組合篩選與價格排序' not in s:
    topic = """
 {
  title:'合適空倉的組合篩選與價格排序',
  steps:[
   '點開候補明細，在「合適空倉」上方展開「據點（可複選）」，勾選想查看的店，可同時選多間；預設全選。',
   '材積可填下限、上限或只填一邊；例如 80～120，包含上下限。指定單一材積可把上下限填成同一數值。',
   '月租排序可選價格低到高或價格高到低；據點、材積與價格排序可同時使用。',
   '查看「顯示 N／總數 間」，按「清除篩選」回復全部據點、不限材積及依據點／倉號排序。'
  ],
  result:'僅篩選這筆候補原本已配對的空倉，不改候補需求、倉位資料或其他人的畫面；關閉後重開明細恢復預設。'
 },
"""
    s, count = re.subn(
        r'(export const waitingManual[\s\S]*?topics\s*:\s*\[)',
        lambda m: m.group(1) + topic,
        s,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到候補操作手冊，未更動檔案。')

changes['src/manual-waiting.ts'] = s

for name, content in changes.items():
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')

print('完成：合適空倉可組合篩選據點、材積與價格排序，操作手冊已更新。')
