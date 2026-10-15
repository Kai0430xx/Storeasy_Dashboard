from pathlib import Path
import re

main = Path('src/main.tsx')
style = Path('src/style.css')
text = main.read_text(encoding='utf-8')
css = style.read_text(encoding='utf-8')

if 'className="activity-card-heading"' not in text:
    pattern = (
        r'(<span className="tag-icon">[\s\S]*?</span>)\s*'
        r'(<span className="badge blue">[\s\S]*?</span>)\s*'
        r'(<span className="badge">[\s\S]*?</span>)'
    )
    text, count = re.subn(
        pattern,
        r'<div className="activity-card-heading">\1'
        r'<div className="activity-card-tags">\2\3</div></div>',
        text,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到活動卡片標籤，未修改任何檔案。')

if '/* activity-card-labels-v1 */' not in css:
    css += '''
/* activity-card-labels-v1 */
.activity-card-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}
.activity-card-heading .tag-icon {
  margin: 0;
  flex: 0 0 auto;
}
.activity-card-tags {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: flex-start;
  gap: 6px;
  min-width: 0;
}
.activity-card-tags > .badge {
  position: static;
  display: inline-block;
  max-width: 100%;
  white-space: normal;
  overflow-wrap: anywhere;
  line-height: 1.5;
}
'''

for path, content in [(main, text), (style, css)]:
    backup = path.with_name(path.name + '.before-activity-label-fix')
    if not backup.exists():
        backup.write_text(
            path.read_text(encoding='utf-8'),
            encoding='utf-8'
        )
    path.write_text(content, encoding='utf-8')

print('已修正活動卡片據點與分類文字重疊。')
