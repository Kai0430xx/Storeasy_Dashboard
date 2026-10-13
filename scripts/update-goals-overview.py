from pathlib import Path
import base64, gzip

root = Path(__file__).resolve().parents[1]
files = {}

def read(name):
    return (root / name).read_text(encoding="utf-8")

def replace(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError("替換位置不唯一：" + old[:80])
    return text.replace(old, new, 1)

if 'from "./GoalsOverview"' in read("src/Targets.tsx"):
    print("全據點目標比較已更新。")
    raise SystemExit(0)

payload = """
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
"""

files["src/GoalsOverview.tsx"] = gzip.decompress(
    base64.b64decode(payload)
).decode("utf-8")

s = read("src/Targets.tsx")
s = 'import GoalsOverview from "./GoalsOverview";\n' + s

s = replace(
    s,
    '  {branches.map(b=>{',
    '''  <GoalsOverview
    branches={branches}
    records={records}
    data={data}
    month={month}
    global={global}
    onEdit={setEditing}
  />
  <details>
    <summary>各據點詳細資料與轉介填寫（點此展開）</summary>
  {branches.map(b=>{''',
)

s = replace(s, '  {editing&&', '  </details>\n  {editing&&')
files["src/Targets.tsx"] = s

s = read("src/targets-api.ts")

s = replace(
    s,
    'period:string,values:any)',
    'period:string,values:any,preserveEmpty=false)',
)

s = replace(
    s,
    '  const next={...goal,period,',
    '''  if(preserveEmpty) {
    for(const k of ["occupancy","performance","referrals"]) {
      if(values[k] === "" || values[k] == null)
        goal[k] = old.data()?.[k] ?? null;
    }
  }
  const next={...goal,period,''',
)

files["src/targets-api.ts"] = s

for name, content in files.items():
    (root / name).write_text(content, encoding="utf-8")
    print("已更新 " + name)
