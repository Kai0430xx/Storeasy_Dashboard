from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
changes = {}

p = root / 'src/WaitingBranches.tsx'
s = p.read_text(encoding='utf-8')
s = re.sub(r'labels\.slice\(0,\s*4\)', 'labels.slice(0,3)', s)
s = re.sub(r'labels\.length\s*>\s*4', 'labels.length>3', s)
changes['src/WaitingBranches.tsx'] = s

p = root / 'src/WaitingList.tsx'
s = p.read_text(encoding='utf-8')
s = s.replace(
    '{r.name}{state.notification(r)',
    '<span>{r.name}</span>{state.notification(r)'
)
changes['src/WaitingList.tsx'] = s

p = root / 'src/waiting-list.css'
s = p.read_text(encoding='utf-8')

if '/* waiting-name-width-v2 */' not in s:
    s += '''
/* waiting-name-width-v2 */
.waiting-summary th:nth-child(1) { width:9%; }
.waiting-summary th:nth-child(2) { width:16%; }
.waiting-summary th:nth-child(3) { width:17%; }
.waiting-summary th:nth-child(4) { width:9%; }
.waiting-summary th:nth-child(5) { width:10%; }
.waiting-summary th:nth-child(6),
.waiting-summary th:nth-child(7) { width:11%; }
.waiting-summary th:nth-child(8) { width:9%; }
.waiting-summary th:nth-child(9) { width:8%; }

.waiting-summary .waiting-name {
 max-width:100%;
 text-align:left;
 align-items:center;
}
.waiting-summary .waiting-name > span {
 min-width:0;
 white-space:normal;
 overflow-wrap:anywhere;
}
.waiting-summary .waiting-name .dot {
 flex-shrink:0;
}
'''
changes['src/waiting-list.css'] = s

p = root / 'src/manual-waiting.ts'
s = p.read_text(encoding='utf-8')
s = s.replace('前四間候補據點', '前三間候補據點')
s = s.replace(
    '前三間候補據點，超過以',
    '前三間候補據點，姓名欄加寬；超過以'
)
changes['src/manual-waiting.ts'] = s

for name, content in changes.items():
    (root / name).write_text(content, encoding='utf-8')

print('完成：姓名欄加寬、據點顯示前三間，操作手冊已同步更新。')
