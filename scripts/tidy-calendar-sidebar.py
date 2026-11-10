from pathlib import Path

root = Path(__file__).resolve().parents[1]
page = root / 'src/CalendarPage.tsx'
css = root / 'src/calendar.css'
manual = root / 'src/manual-content.ts'
marker = '// calendar-sidebar-v5'
source = page.read_text(encoding='utf-8')

if marker not in source:
    start = source.index(' const legend=')
    end = source.index('\n const eventButton=', start)
    source = source[:start] + ''' // calendar-sidebar-v5
 const legend:CalRow[]=categories.rows.filter(c=>!c.archived).map(c=>({key:uid+':'+c.id,name:c.name,color:c.color,edit:c}));
 for(const e of data.events){const key=e.ownerId+':'+e.categoryId;if(!legend.some(c=>c.key===key))legend.push({key,name:e.categoryName+(e.ownerId===uid?'':` · ${e.ownerName}`),color:e.color,edit:null});}
''' + source[end:]

    start = source.index(
        '{categories.rows.filter(c=>!c.archived).map(c=><div className="calendar-category"'
    )
    end = source.index('<p className="hint">點日期新增。', start)

    source = source[:start] + '''<div className="calendar-category-list">{legend.map(c=><div className="calendar-category-row" key={c.key}><label className="calendar-check"><input type="checkbox" aria-label={`顯示分類 ${c.name}`} checked={!hidden.includes(c.key)} onChange={e=>setHidden(v=>e.target.checked?v.filter(k=>k!==c.key):[...v,c.key])}/><i className="calendar-color" style={{background:c.color}}/><span>{c.name}</span></label>{c.edit&&<button type="button" className="text-button" aria-label={`編輯分類 ${c.name}`} onClick={()=>setCategory({...c.edit})}>編輯</button>}</div>)}</div>{!legend.length&&<p className="hint">尚未建立分類，可先用未分類。</p>}
  ''' + source[end:]

    source = source.replace(
        '<h2>我的分類</h2>', '<h2>分類</h2>'
    )
    source = source.replace(
        '{b.name} · 全部人員</option>', '{b.name}</option>'
    )

if (
    '<h3>顯示分類</h3>' in source
    or '{b.name} · 全部人員</option>' in source
):
    raise SystemExit(
        '頁面版本不同，尚未修改檔案。請提供錯誤訊息。'
    )

style = css.read_text(encoding='utf-8')
if '/* calendar-sidebar-v5 */' not in style:
    style += '''
/* calendar-sidebar-v5 */
.calendar-category-list{display:flex;flex-direction:column;gap:6px;min-width:0;width:100%}
.calendar-category-row{display:flex;align-items:center;gap:6px;min-width:0}
.calendar-category-row .calendar-check{flex:1;min-width:0;margin:4px 0!important;gap:6px}
.calendar-category-row .calendar-check span{min-width:0;overflow-wrap:anywhere}
.calendar-category-row .calendar-color{margin-right:0}
.calendar-category-row>.text-button{flex-shrink:0;padding:6px 2px}
@media(max-width:1100px){.calendar-category-list{flex-basis:100%;display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:4px 14px}}
'''

text = manual.read_text(encoding='utf-8')
if '// calendar-sidebar-v5-manual' not in text:
    text += '''
// calendar-sidebar-v5-manual
manualPages.find(p=>p.id==='calendar')?.topics.push({title:'分類清單與據點名稱',steps:['左側統一顯示一份「分類」清單，每個分類同一列提供勾選框、顏色、名稱；自己的有效分類旁有「編輯」，上方「＋新增」可建立分類。','取消勾選只隱藏該分類行程，不刪除行程或改變分享對象；再次勾選即顯示。編輯按鈕不會切換勾選狀態。','分享給自己的行程及據點模式中其他人的分類也顯示在同一清單，名稱後保留建立者以區分同名分類；只能編輯自己的分類。','主管／管理員的日曆據點選單只顯示店名，移除「全部人員」後綴；切換據點的查看範圍維持不變。'],result:'分類不再重複列出，篩選、分類管理與日曆權限維持原功能。'});
'''

for path, content in [
    (page, source),
    (css, style),
    (manual, text),
]:
    if path.read_text(encoding='utf-8') != content:
        path.write_text(content, encoding='utf-8')

print('日曆分類已合併，據點名稱已簡化。本次不需部署 Firebase。')
