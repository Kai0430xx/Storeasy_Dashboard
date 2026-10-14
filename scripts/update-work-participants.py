from pathlib import Path

root = Path(__file__).resolve().parents[1]
marker = 'storeasy-work-participants-v1'
files = {}

p = root / 'src/WorkTasks.tsx'
s = p.read_text(encoding='utf-8')

if marker not in s:
    old = "<small>{Object.values(t.branchNames).join('、')}{t.mode==='shared'?' · 共同協作':''}</small>"
    new = "<small>{t.branchIds.length>1?`共同協作 · 參與 ${t.branchIds.length} 間據點`:(t.branchNames?.[t.branchIds[0]]||'未命名據點')}</small>"

    if s.count(old) != 1:
        raise RuntimeError('找不到據點摘要，尚未寫入')

    s = s.replace(old, new, 1)

    old = '<p className="work-description">{item.description}</p>'
    new = old + """{task.branchIds.length>1&&<details className="work-participants" key={`${task.id}:${thread}`}><summary>查看參與據點（{task.branchIds.length} 間）</summary><ul>{task.branchIds.map((id:string)=><li key={id}>{task.branchNames?.[id]||'未命名據點'}</li>)}</ul></details>}"""

    if s.count(old) != 1:
        raise RuntimeError('找不到事項內容，尚未寫入')

    s = s.replace(old, new, 1)
    files[str(p)] = s + '\n// ' + marker + '\n'

p = root / 'src/work-tasks.css'
s = p.read_text(encoding='utf-8')

if marker not in s:
    files[str(p)] = s + """
/* storeasy-work-participants-v1 */
.work-participants{margin:10px 0;font-size:13px;color:#526a8c}
.work-participants summary{cursor:pointer;width:fit-content;color:#173f75;padding:5px 0}
.work-participants summary:focus-visible{outline:2px solid #173f75;outline-offset:3px}
.work-participants ul{display:flex;flex-wrap:wrap;gap:8px;list-style:none;padding:0;margin:8px 0;max-height:150px;overflow:auto}
.work-participants li{background:#f0f4fa;border:1px solid #e0e7f1;border-radius:6px;padding:5px 9px;overflow-wrap:anywhere}
"""

for name, content in files.items():
    Path(name).write_text(content, encoding='utf-8')
    print('已更新 ' + name)

print('完成：左側僅顯示參與間數，右側名單預設收合。本次不需要修改 Firebase 規則。')
