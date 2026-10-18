from pathlib import Path
import re

r = Path(__file__).resolve().parents[1]
if (
    'mobile-pages-v2.css' in (r / 'src/main.tsx').read_text()
    and 'mobile-pages-v2-manual' in (r / 'src/manual-content.ts').read_text()
):
    print('手機版更新已套用。')
    raise SystemExit(0)

changes = {}

p = r / 'src/WorkTasks.tsx'
s = p.read_text()
s = s.replace(
    'return <section className="work-area">',
    """return <section className={'work-area'+(selected?' mobile-work-detail':'')}>
  {selected&&<div className="mobile-work-backbar"><button type="button" disabled={busy} onClick={()=>{setSelected('');setThread('main');}}>← 返回待辦</button>{thread!=='main'&&<button type="button" disabled={busy} onClick={()=>setThread('main')}>返回主事項</button>}</div>}"""
)

anchor = " const notificationBox=useRef<HTMLDetailsElement>(null);"
mobile_effect = """
 // mobile-work-screen-v2
 useEffect(()=>{
  if(!selected)return;
  const media=window.matchMedia('(max-width:760px)');
  const previous=document.body.style.overflow,scroll=window.scrollY;
  const sync=()=>{document.body.classList.toggle('mobile-work-focused',media.matches);document.body.style.overflow=media.matches?'hidden':previous;};
  sync();media.addEventListener('change',sync);
  return()=>{media.removeEventListener('change',sync);document.body.classList.remove('mobile-work-focused');document.body.style.overflow=previous;if(media.matches)window.scrollTo({top:scroll});};
 },[selected]);
"""
assert anchor in s
s = s.replace(anchor, anchor + mobile_effect)

anchor = '<div className="work-messages" aria-label="對話訊息">'
nav = """<nav className="mobile-work-threads" aria-label="子項目切換"><button type="button" className={thread==='main'?'selected':''} onClick={()=>setThread('main')}>主事項</button>{items.filter(i=>!i.deleted||(global&&task?.deleted)).map(i=><button type="button" key={i.id} className={thread===i.id?'selected':''} onClick={()=>choose(task.id,i.id)}>{i.title}{unread.includes(i.id)&&dot}</button>)}</nav>
    """
assert anchor in s
s = s.replace(anchor, nav + anchor)
changes[p] = s

p = r / 'src/GoalsOverview.tsx'
s = p.read_text()
start = s.index('<button disabled={busy} onClick={async()=>')
end = s.index('</button>', start) + len('</button>')
s = s[:start] + '{global&&' + s[start:end] + '}' + s[end:]
changes[p] = s

p = r / 'src/main.tsx'
s = p.read_text()
s = s.replace(
    'import "./mobile-layout.css";',
    'import "./mobile-layout.css";\nimport "./mobile-pages-v2.css";'
)

a = s.index('{page === "units" && (')
b = s.index('{page === "activities" && (', a)
section = s[a:b]
section = section.replace(
    '<table>', '<table className="mobile-unit-table">', 1
).replace(
    '<table>', '<table className="mobile-events-table">', 1
)

sort = """<div className="mobile-unit-sort"><label>排序<select aria-label="手機倉位排序" value={unitSort} onChange={e=>setUnitSort(e.target.value)}><option value="code">倉位編號</option><option value="volume">材積由小到大</option></select></label></div>"""
section = section.replace(
    '<div className="table-wrap">',
    sort + '<div className="table-wrap">',
    1
)

tables = [
    ('mobile-unit-table', [
        '倉位／據點', '尺寸', '材積', '月租', '狀態',
        '租期', '空倉起始日', '備註', '操作'
    ]),
    ('mobile-events-table', [
        '日期', '倉位／據點', '類型', '使用活動',
        '異動當時牌價', '退租原因', '更正'
    ])
]

for cls, labels in tables:
    begin = section.index('<table className="' + cls + '">')
    start = section.index('<tbody>', begin)
    end = section.index('</tbody>', start)
    body = section[start:end]
    if (
        cls == 'mobile-events-table'
        and body.index('priceSnapshot') < body.index('.activities')
    ):
        labels[3], labels[4] = labels[4], labels[3]
    values = iter(labels)
    chunk = re.sub(
        r'<td(?=[\s>])',
        lambda m: '<td data-label="' + next(values) + '"',
        body
    )
    section = section[:start] + chunk + section[end:]

s = s[:a] + section + s[b:]
changes[p] = s

goal_tables = [
    ('MonthlyGoalsTable.tsx', [
        '據點', '出租率目標／實際', '業績完成率目標／實際',
        '其它目標／實際', '轉介目標／實際', '設定', '是否達標'
    ]),
    ('AnnualGoalsTable.tsx', [
        '據點', '業績目標／已結束月份平均',
        '剩餘月份平均需', '轉介達標月份數', '設定'
    ])
]

for name, labels in goal_tables:
    p = r / 'src' / name
    s = p.read_text().replace(
        '<table aria-label=',
        '<table className="mobile-goal-table" aria-label='
    )
    values = iter(labels)
    s = re.sub(
        r'<td(?=[\s>])',
        lambda m: '<td data-label="' + next(values) + '"',
        s
    )
    changes[p] = s

p = r / 'src/manual-content.ts'
s = p.read_text()
s = s.replace(
    '在營運總覽點「匯出 YYYY 年度目標與轉介 Excel」',
    '主管／管理員可在營運總覽點「匯出 YYYY 年度目標與轉介 Excel」'
)
s += """
// mobile-pages-v2-manual
manualPages.find(p=>p.id==='work')?.topics.push({title:'手機單一事項與返回待辦',steps:['手機點事項後切換為該事項的完整畫面，不再同時顯示上方清單與下方重複內容；頂端固定「返回待辦」。','點「返回待辦」保留原本的分類、搜尋、完成狀態及清單位置；子項目可從內容中的「子項目切換」選擇，也能返回主事項。','一般頁面的頂端選單列固定，捲動後仍可切換頁面；事項內容須先返回待辦，再切換其它分頁。新增及編輯視窗保留自己的固定標題與關閉按鈕。'],result:'電腦仍使用原本左右雙欄；手機的返回不會刪除已儲存內容，尚未送出的對話文字須自行確認。'});
manualPages.find(p=>p.id==='units')?.topics.push({title:'手機倉位卡片與異動紀錄',steps:['手機將每個倉位顯示為獨立卡片，包含倉號、據點、尺寸、材積、月租、狀態、租期、備註及操作，不需左右滑動對照行數。','卡片上方的「排序」可切換倉號或材積；空倉篩選時保留空倉起始日。異動紀錄也採逐筆卡片。'],result:'承租、續約、退租、轉倉及編輯沿用原有流程，電腦保留表格。'});
manualPages.find(p=>p.id==='waiting')?.topics.push({title:'手機候補卡片欄位',steps:['姓名在卡片左上角，登記日期在右上角；候補據點獨立占一整排，其餘需求與狀態在下方排列。'],result:'僅調整手機呈現，不更動候補資料與配對。'});
manualPages.find(p=>p.id==='targets')?.topics.push({title:'手機目標卡片及年度匯出權限',steps:['手機將目標區標題、年度一覽及設定按鈕分行顯示，月目標與年目標用有欄位名稱的卡片呈現，避免文字擠成直排。','「匯出 YYYY 年度目標與轉介 Excel」僅主管與管理員可見，手機與電腦相同；店長仍可查看有權限的目標與年度一覽。'],result:'匯出只讀取資料，手機排版不更動 KPI、目標與轉介。'});
"""
changes[p] = s

changes[r / 'src/mobile-pages-v2.css'] = r"""
/* mobile-pages-v2 */
.mobile-work-backbar,.mobile-work-threads,.mobile-unit-sort {
 display:none;
}
@media(max-width:760px) {
 main > header {
  position:sticky; top:0; z-index:15;
  padding-top:max(10px,env(safe-area-inset-top));
 }
 .mobile-work-focused main > header {
  visibility:hidden; pointer-events:none;
 }
 .work-area:not(.mobile-work-detail) .work-layout {
  display:block; height:auto; min-height:0;
 }
 .work-area:not(.mobile-work-detail) .work-list {
  max-height:none; overflow:visible; border:0;
 }
 .work-area:not(.mobile-work-detail) .work-conversation {
  display:none;
 }
 .work-area.mobile-work-detail {
  position:fixed; inset:0; z-index:30; background:#f5f7fa;
  display:flex; flex-direction:column; overflow:hidden;
  padding-top:env(safe-area-inset-top);
  padding-bottom:env(safe-area-inset-bottom);
 }
 .mobile-work-detail > .work-toolbar,
 .mobile-work-detail > .work-categories,
 .mobile-work-detail > .work-filters {
  display:none;
 }
 .mobile-work-detail > .alert {
  flex-shrink:0; margin:0; max-height:20dvh; overflow:auto;
 }
 .mobile-work-backbar {
  display:flex; justify-content:space-between; gap:8px;
  align-items:center; flex-shrink:0; min-height:56px;
  padding:6px 12px; background:white;
  border-bottom:1px solid #dce5f1;
 }
 .mobile-work-backbar button {
  min-height:44px; color:#173f75; font-weight:600;
 }
 .mobile-work-detail .work-layout {
  flex:1; min-height:0; height:auto; display:flex;
  border:0; border-radius:0;
 }
 .mobile-work-detail .work-list { display:none; }
 .mobile-work-detail .work-conversation {
  display:flex; flex:1; min-height:0; width:100%;
  overflow-y:auto; overscroll-behavior:contain;
 }
 .mobile-work-detail .work-detail {
  display:block; flex-shrink:0; max-height:none;
  overflow:visible; height:auto; padding:16px;
 }
 .mobile-work-detail .work-detail .work-toolbar {
  align-items:flex-start; flex-wrap:nowrap;
 }
 .mobile-work-detail .work-detail h2 {
  font-size:20px; line-height:1.5; overflow-wrap:anywhere;
 }
 .mobile-work-detail .work-complete { flex-shrink:0; }
 .mobile-work-detail .work-messages {
  flex:1 0 auto; overflow:visible; min-height:180px;
 }
 .mobile-work-detail .work-composer {
  position:sticky; bottom:0; flex-shrink:0; background:white;
  padding-bottom:max(10px,env(safe-area-inset-bottom));
 }
 .mobile-work-threads {
  display:flex; flex-wrap:wrap; gap:8px; padding:12px 16px;
  border-bottom:1px solid #dce5f1;
 }
 .mobile-work-threads button {
  min-height:40px; padding:8px 10px;
  border:1px solid #dce5f1; background:white;
  white-space:normal; overflow-wrap:anywhere; max-width:100%;
 }
 .mobile-work-threads .selected {
  background:#173f75; color:white;
 }
 .target-panel > .panel-heading {
  display:grid; grid-template-columns:minmax(0,1fr);
  align-items:stretch; gap:10px; padding:18px;
 }
 .target-panel > .panel-heading h2 {
  margin:0 0 4px; white-space:normal;
 }
 .target-panel > .panel-heading > button {
  width:100%; min-width:0; justify-content:flex-start;
  text-align:left; white-space:normal; word-break:normal;
  line-height:1.6; padding:10px 12px;
  border:1px solid #dce5f1; min-height:44px;
 }
 .mobile-unit-sort {
  display:flex; padding:12px 16px;
  border-bottom:1px solid #e6ebf1;
 }
 .mobile-unit-sort label {
  display:flex; flex-direction:row; align-items:center;
  gap:12px; margin:0; width:100%;
 }
 .mobile-unit-sort select { flex:1; min-width:0; }
 table.mobile-unit-table,table.mobile-events-table,
 table.mobile-goal-table {
  display:block; width:100%; min-width:0;
  white-space:normal; table-layout:fixed;
 }
 .mobile-unit-table thead,.mobile-events-table thead,
 .mobile-goal-table thead { display:none; }
 .mobile-unit-table tbody,.mobile-events-table tbody,
 .mobile-goal-table tbody { display:block; width:100%; }
 .mobile-unit-table tr,.mobile-events-table tr,
 .mobile-goal-table tr {
  display:grid; grid-template-columns:repeat(2,minmax(0,1fr));
  gap:14px 12px; padding:16px;
  border-bottom:1px solid #dce5f1;
 }
 .mobile-unit-table td,.mobile-events-table td,
 .mobile-goal-table td {
  display:block; min-width:0; max-width:none; border:0;
  padding:0; white-space:normal; overflow-wrap:anywhere;
 }
 .mobile-unit-table td::before,.mobile-events-table td::before,
 .mobile-goal-table td::before {
  content:attr(data-label); display:block; font-size:12px;
  font-weight:400; color:#7c899b; margin-bottom:5px;
 }
 .mobile-unit-table td:first-child {
  grid-column:1; grid-row:1;
 }
 .mobile-unit-table td:first-child strong { font-size:19px; }
 .mobile-unit-table td[data-label="狀態"] {
  grid-column:2; grid-row:1;
 }
 .mobile-unit-table td[data-label="租期"],
 .mobile-unit-table td[data-label="空倉起始日"],
 .mobile-unit-table td[data-label="備註"],
 .mobile-unit-table td[data-label="操作"] {
  grid-column:1/-1;
 }
 .mobile-unit-table .row-actions {
  display:flex; flex-wrap:wrap; gap:10px;
 }
 .mobile-unit-table .row-actions button {
  min-height:40px; padding:6px 10px;
  border:1px solid #dce5f1;
 }
 .mobile-events-table td[data-label="使用活動"],
 .mobile-events-table td[data-label="退租原因"],
 .mobile-events-table td[data-label="更正"] {
  grid-column:1/-1;
 }
 .mobile-goal-table tr {
  grid-template-columns:minmax(0,1fr);
 }
 .mobile-goal-table td:first-child {
  font-weight:600; font-size:17px;
 }
 .mobile-goal-table td:empty { display:none; }
 .mobile-goal-table td > span {
  display:block; margin-top:4px;
 }
 .mobile-goal-table td button {
  min-height:40px; white-space:normal; text-align:left;
 }
 .waiting-summary td:nth-child(2) {
  grid-column:1; grid-row:1;
 }
 .waiting-summary td:nth-child(1) {
  grid-column:2; grid-row:1; text-align:right;
 }
 .waiting-summary td:nth-child(3) {
  grid-column:1/-1; grid-row:2;
 }
}
"""

# 全部轉換成功後才寫檔。
for path, content in changes.items():
    path.write_text(content, encoding='utf-8')

print('已更新手機排版、年度匯出權限及操作手冊。')
