from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
changes = {}

p = root / 'src/WaitingList.tsx'
s = p.read_text(encoding='utf-8')

if 'className="waiting-detail-status"' not in s:
    pattern = (
        r'<div className="waiting-status-tabs">'
        r'(?=\s*<label>)([\s\S]*?)</div>'
    )
    s, count = re.subn(
        pattern,
        lambda m: (
            '<fieldset className="waiting-detail-status">'
            '<legend>候補狀態</legend>'
            '<div className="waiting-status-tabs">'
            + m.group(1)
            + '</div></fieldset>'
        ),
        s,
        count=1,
    )
    if count != 1:
        raise SystemExit('找不到候補狀態區塊，未變更檔案')

changes['src/WaitingList.tsx'] = s

p = root / 'src/waiting-list.css'
s = p.read_text(encoding='utf-8')

if '/* waiting-detail-status-v1 */' not in s:
    s += '''
/* waiting-detail-status-v1 */
.modal fieldset.waiting-detail-status {
  padding:16px;
  margin:24px 0 28px;
  max-height:none;
  overflow:visible;
  background:#f6f8fb;
  border:1px solid #dae3ed;
}
.waiting-detail-status > legend {
  font-size:14px;
  font-weight:600;
  padding:0 6px;
}
.waiting-detail-status > .waiting-status-tabs {
  gap:12px 20px;
}
.waiting-detail-status .waiting-status-tabs > label {
  min-height:44px;
  padding:10px 16px;
  margin:0;
  border:1px solid #d7e1ed;
  border-radius:8px;
  background:white;
  font-size:14px;
  line-height:1.5;
  white-space:nowrap;
  cursor:pointer;
}
.waiting-detail-status + h3 {
  margin:0 0 14px;
}
'''

changes['src/waiting-list.css'] = s

p = root / 'src/manual-waiting.ts'
s = p.read_text(encoding='utf-8')

old = '「已承租」與「已取消」只能擇一；取消勾選後恢復候補中。'
new = '在候補明細的「候補狀態」區塊勾選「已承租」或「已取消」，只能擇一；取消勾選後恢復候補中。'

if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit('找不到候補狀態操作說明，未變更檔案')

changes['src/manual-waiting.ts'] = s

for name, text in changes.items():
    target = root / name
    backup = root / '.update-backups' / 'waiting-status-v1' / name
    backup.parent.mkdir(parents=True, exist_ok=True)

    if not backup.exists():
        backup.write_text(
            target.read_text(encoding='utf-8'),
            encoding='utf-8',
        )

    target.write_text(text, encoding='utf-8')

print('已調整候補狀態選項與標題間距，並更新操作手冊')
