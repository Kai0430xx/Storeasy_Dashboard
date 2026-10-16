from pathlib import Path
import re

marker = '/* storeasy-sticky-modal-headers-v1 */'
style = Path('src/style.css')
css = style.read_text(encoding='utf-8')
changes = {}

def edit(name, pattern, replacement, expected):
    text = changes.get(name, Path(name).read_text(encoding='utf-8'))
    text, count = re.subn(pattern, replacement, text)
    if count != expected:
        raise SystemExit(
            f'版本不符：{name}（{count}/{expected}），'
            '未修改任何檔案。'
        )
    changes[name] = text

if marker not in css:
    pattern = (
        r'(<button\b[^>]*aria-label="關閉"[\s\S]*?</button>)'
        r'\s*(<h2>[\s\S]*?</h2>)'
    )

    for name, count in [
        ('src/MonthlyEntry.tsx', 1),
        ('src/Targets.tsx', 2),
        ('src/GoalsOverview.tsx', 1)
    ]:
        edit(
            name,
            pattern,
            r'<div className="modal-heading">\2\1</div>',
            count
        )

    edit(
        'src/YearGoalsView.tsx',
        r'className="panel-heading"',
        'className="panel-heading modal-heading"',
        1
    )

    edit(
        'src/WorkTasks.tsx',
        r'<div className="work-toolbar"><h2>\{title\}</h2>',
        '<div className="work-toolbar modal-heading"><h2>{title}</h2>',
        1
    )

    edit(
        'src/ImportSources.tsx',
        r'<h2>刪除匯入資料</h2>',
        '<div className="modal-heading"><h2>刪除匯入資料</h2>'
        '<button type="button" aria-label="關閉" disabled={busy} '
        'onClick={()=>setPending(null)}>×</button></div>',
        1
    )

    changes[str(style)] = css + '''
/* storeasy-sticky-modal-headers-v1 */
.modal > .modal-heading {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  flex-direction: row;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin: 0 0 18px;
  padding: 10px 0 14px;
  background: #fff;
  border-bottom: 1px solid #e3eaf3;
  box-shadow: 0 -30px 0 #fff;
}
.modal > .modal-heading h2 {
  min-width: 0;
  margin: 0;
  font-size: 18px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.modal > .modal-heading > button {
  position: static;
  flex: 0 0 36px;
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  margin: 0;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #263d5a;
  font-size: 24px;
  line-height: 1;
}
.modal > .modal-heading > button:hover:enabled {
  background: #edf2f8;
}
'''

name = 'src/ActivityUsage.tsx'
text = Path(name).read_text(encoding='utf-8')

if '活動分類：' not in text:
    text, count = re.subn(
        r'(<h2>\s*\{activity\.name\}\s*·\s*使用明細\s*</h2>)',
        r'\1<p>活動分類：<strong>'
        r'{activity.category || "未分類"}</strong></p>',
        text,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到活動使用明細標題，未修改任何檔案。')
    changes[name] = text

for name, content in changes.items():
    path = Path(name)
    backup = path.with_name(path.name + '.before-modal-and-category')
    if not backup.exists():
        backup.write_text(
            path.read_text(encoding='utf-8'),
            encoding='utf-8'
        )
    path.write_text(content, encoding='utf-8')

print('已固定所有視窗標題，並在活動使用明細顯示分類。')
