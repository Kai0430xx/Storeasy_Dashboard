
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
