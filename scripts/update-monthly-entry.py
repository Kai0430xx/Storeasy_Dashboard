from pathlib import Path
import base64, gzip, json, re

root = Path(__file__).resolve().parents[1]
files = {}

def read(name):
    return (root / name).read_text(encoding="utf-8")

def replace(s, old, new):
    if s.count(old) != 1:
        raise RuntimeError("找不到唯一替換位置：" + old[:80])
    return s.replace(old, new, 1)

payload = """
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
/Nb4Q7pBHpVAlCPjdTz9N6tfIFtdIgAA
"""

modules = json.loads(gzip.decompress(base64.b64decode(payload)))

for name in ["src/actuals.js", "src/MonthlyEntry.tsx"]:
    files[name] = modules[name]

s = read("src/GoalsOverview.tsx")
if 'from "./MonthlyEntry"' not in s:
    s = (
        'import MonthlyEntry from "./MonthlyEntry";\n'
        'import { effectiveMonths } from "./actuals.js";\n'
        + s
    )
    s = replace(
        s, "['targets','referrals']",
        "['targets','referrals','actuals']",
    )
    s = replace(
        s, 'const goal=(b:Row,p:string)',
        'const monthsFor=(b:Row)=>effectiveMonths(data[b.id]?.months||[],records[b.id]?.actuals||[]);\n'
        ' const goal=(b:Row,p:string)',
    )
    s = replace(
        s, 'm=data[b.id]?.months?.find(',
        'm=monthsFor(b).find(',
    )
    s = replace(
        s, 'data[b.id]?.months||[],referrals(b)',
        'monthsFor(b),referrals(b)',
    )

    start = s.index('<table aria-label="每月目標比較"')
    end = s.index('<h3>{year}', start)

    block = replace(
        s[start:end],
        '<th>據點</th>',
        '<th>據點</th><th>本月實際數值</th>',
    )
    block = replace(
        block,
        '<td>{b.name}</td>',
        '<td>{b.name}{m?.manualActuals&&<small className="table-sub">含手動修正</small>}</td>'
        '<td><MonthlyEntry branch={b} month={month} /></td>',
    )
    s = s[:start] + block + s[end:]

files["src/GoalsOverview.tsx"] = s

s = read("src/Targets.tsx")
if 'from "./actuals.js"' not in s:
    s = 'import { effectiveMonths } from "./actuals.js";\n' + s
    s = replace(
        s, "['targets','referrals','targetHistory']",
        "['targets','referrals','targetHistory','actuals']",
    )
    s = replace(
        s, 'const months=data[b.id]?.months||[]',
        'const months=effectiveMonths(data[b.id]?.months||[],r.actuals||[])',
    )
    s = replace(
        s, '<h3>{month} 每月目標</h3>',
        '<h3>{month} 每月目標</h3>{kpi?.manualActuals&&<p>'
        '此月包含手動修正值；原 KPI 保留，可在上方「輸入／修正本月數值」查看及恢復。'
        '</p>}',
    )

files["src/Targets.tsx"] = s

s = read("src/targets.js")
if 'const corrected=months.find' not in s:
    s = replace(
        s,
        'const occupancy=currentYear?',
        'const corrected=months.find(m=>(m.id||m.month)===today.slice(0,7)&&m.manualOccupancy);\n'
        '  const occupancy=currentYear&&corrected?corrected.kpiMetrics.occupancy:currentYear?',
    )
    s = replace(
        s,
        'Math.ceil(total*goal.occupancy/100-1e-9)-rented',
        '(currentYear&&corrected?Math.ceil(total*Math.max(0,goal.occupancy-occupancy)/100-1e-9):Math.ceil(total*goal.occupancy/100-1e-9)-rented)',
    )

files["src/targets.js"] = s

if (root / "src/annual-export.ts").exists():
    s = read("src/annual-export.ts")
    if 'from "./actuals.js"' not in s:
        s = 'import { effectiveMonths } from "./actuals.js";\n' + s
        s = replace(
            s, 'kpi=r.months?.find(',
            'kpi=effectiveMonths(r.months||[],r.actuals||[]).find(',
        )
        s = replace(
            s, "['targets','months','referrals']",
            "['targets','months','referrals','actuals']",
        )
        s = replace(
            s,
            "kpiFile:kpi?.sourceFile||'未匯入'",
            "kpiFile:(kpi?.sourceFile||'未匯入')+(kpi?.manualActuals?'（手動修正：'+(r.actuals?.find((a:Row)=>(a.id||a.month)===month)?.reason||'')+'）':'')",
        )
    files["src/annual-export.ts"] = s

s = read("firestore.rules")
if 'match /actuals/{month}' not in s:
    s, count = re.subn(
        r'(?m)^(\s*)match /imports/\{importId\} \{',
        lambda m: modules["rules"] + m.group(0),
        s,
        count=1,
    )
    if count != 1:
        raise RuntimeError("找不到 Firebase 規則插入位置")

files["firestore.rules"] = s

for name, content in files.items():
    (root / name).write_text(content, encoding="utf-8")
    print("已更新 " + name)
