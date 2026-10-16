import {useRef,useState} from 'react';
import SearchInput from './SearchInput';
import {manualPages} from './manual-content';
import './operation-manual.css';

export default function OperationManual(){
 const [selected,setSelected]=useState('dashboard');
 const [search,setSearch]=useState('');
 const content=useRef<HTMLDivElement>(null);

 const normalize=(v:string)=>
  v.normalize('NFKC').toLocaleLowerCase().replace(/\s+/g,'');

 const query=normalize(search.trim());

 const groups=query
  ?manualPages.map(p=>({
    ...p,
    topics:p.topics.filter(t=>
     normalize([
      p.title,p.intro,t.title,...t.steps,t.result
     ].join(' ')).includes(query)
    )
   })).filter(p=>p.topics.length)
  :manualPages.filter(p=>p.id===selected);

 const count=groups.reduce((n,p)=>n+p.topics.length,0);

 function choose(id:string){
  setSelected(id);
  setSearch('');
  content.current?.scrollIntoView({
   block:'start',
   behavior:'smooth'
  });
 }

 return <div className="operation-manual">
  <section className="panel manual-search">
   <div>
    <strong>依頁面查操作</strong>
    <p>選擇左側章節，或搜尋按鈕名稱與操作內容。手冊更新：2026/10/16。</p>
   </div>
   <SearchInput
    aria-label="搜尋操作手冊"
    placeholder="搜尋手冊，例如：未付款、轉倉、轉介"
    value={search}
    onChange={e=>setSearch(e.target.value)}
    onClear={()=>setSearch('')}
   />
  </section>

  <div className="manual-layout">
   <aside className="panel manual-index" aria-label="操作手冊章節">
    <h2>頁面目錄</h2>
    {manualPages.map((p,i)=>
     <button
      key={p.id}
      type="button"
      aria-current={!query&&p.id===selected?'page':undefined}
      onClick={()=>choose(p.id)}
     >
      <span>{String(i+1).padStart(2,'0')}</span>
      {p.title}
     </button>
    )}
   </aside>

   <div className="manual-content" ref={content}>
    <label className="manual-mobile-index">
     選擇教學頁面
     <select
      aria-label="選擇手冊章節"
      value={selected}
      onChange={e=>choose(e.target.value)}
     >
      {manualPages.map(p=>
       <option key={p.id} value={p.id}>{p.title}</option>
      )}
     </select>
    </label>

    {query&&
     <p role="status" className="manual-results">
      找到 {count} 項相關說明
     </p>
    }

    {!groups.length&&
     <section className="panel manual-empty">
      <h2>找不到符合的操作說明</h2>
      <p>請縮短關鍵字，例如「續約」「匯入」或「指派」。</p>
      <button
       type="button"
       className="secondary"
       onClick={()=>setSearch('')}
      >清除搜尋</button>
     </section>
    }

    {groups.map(p=>
     <section
      className="panel manual-chapter"
      aria-label={`${p.title}操作教學`}
      key={p.id}
     >
      <div className="manual-chapter-heading">
       <small>頁面操作教學</small>
       <h2>{p.title}</h2>
       <p>{p.intro}</p>
       <p className="manual-access">{p.access}</p>
      </div>

      {p.topics.map((t,i)=>
       <article className="manual-topic" key={t.title}>
        <h3><span>{i+1}</span>{t.title}</h3>
        <ol>
         {t.steps.map(step=><li key={step}>{step}</li>)}
        </ol>
        <div className="manual-result">
         <strong>完成後／資料影響</strong>
         <p>{t.result}</p>
        </div>
       </article>
      )}
     </section>
    )}
   </div>
  </div>
 </div>;
}
