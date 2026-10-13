from pathlib import Path
import base64, gzip, json, re

root = Path(__file__).resolve().parents[1]
files = {}

def read(name):
    return (root / name).read_text(encoding="utf-8")

def replace(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError("替換位置不唯一：" + old[:80])
    return text.replace(old, new, 1)

def sub(text, pattern, replacement):
    text, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise RuntimeError("找不到替換位置：" + pattern[:80])
    return text

if 'from "./Targets"' in read("src/main.tsx"):
    print("目標與轉介功能已更新。")
    raise SystemExit(0)

payload = """
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
"""

modules = json.loads(gzip.decompress(base64.b64decode(payload)))

for name in ["src/targets.js", "src/targets-api.ts", "src/Targets.tsx"]:
    files[name] = modules[name]

s = read("src/imports.js")
s = 'import { kpiMetrics } from "./targets.js";\n' + s
s = replace(
    s,
    'amounts: kpiAmounts(rows, column),',
    'amounts: kpiAmounts(rows, column), kpiMetrics: kpiMetrics(rows, column, year),',
)
files["src/imports.js"] = s

s = read("src/api.ts")
s = 'import { exitCategories, vacancyDate } from "./targets.js";\n' + s

s = replace(
    s,
    'const previousLease = {',
    '''const exitCategory = type === "exit" ? String(data.exitCategory || "") : "";
        if (type === "exit" && !exitCategories.includes(exitCategory))
          throw new Error("請選擇退租原因分類");
        const previousLease = {
          vacantSince: unit.vacantSince || null,''',
)

s = sub(
    s,
    r'(transaction.update\(unitDoc,\s*\{\s*\.\.\.lease,)',
    lambda m: m.group(1) + '\n          vacantSince: type === "exit" ? date : null,',
)

s = replace(s, '          exitReason,', '          exitReason, exitCategory,')

s = replace(
    s,
    '          status: event.type === "new" ? "vacant" : "rented",',
    '          vacantSince: event.type === "new" ? event.previousLease?.vacantSince || null : null,\n'
    '          status: event.type === "new" ? "vacant" : "rented",',
)

s = replace(
    s,
    '                    status: "vacant",',
    '                    vacantSince: null, status: "vacant",',
)

s = replace(
    s,
    '          status: vacant.has(unit.code)',
    '          vacantSince: vacancyDate(previousUnits.get(unit.code), vacant.has(unit.code) ? "vacant" : "rented", data.effectiveDate),\n'
    '          status: vacant.has(unit.code)',
)

s = replace(
    s,
    '              amounts: frozenAmounts(',
    '              kpiMetrics: month.kpiMetrics || {revenue:null,performance:null,occupancy:null},\n'
    '              amounts: frozenAmounts(',
)
files["src/api.ts"] = s

s = read("src/main.tsx")
s = 'import Targets, { VacancyCell, OperationsInsights, exitCategories } from "./Targets";\n' + s

s = replace(
    s,
    '["imports", "資料匯入", Upload],',
    '["imports", "資料匯入", Upload],\n'
    '    ["targets", "目標與轉介", LayoutDashboard],',
)

s = replace(
    s,
    '{page === "units" && (',
    '''{page === "dashboard" && <>
                <section className="panel target-panel">
                  <h2>營運目標與轉介</h2>
                  <button className="primary" onClick={()=>setPage("targets")}>
                    查看每月／年度目標與轉介
                  </button>
                </section>
                <OperationsInsights units={units} events={events} />
              </>}
              {page === "targets" && <Targets
                branches={branches.filter(b=>!b.archived && (branchId === "all" || b.id === branchId))}
                month={month}
                profile={profile}
                data={data}
              />}
              {page === "units" && (''',
)

s = replace(
    s,
    ': "管理註冊申請、角色與據點存取權限。"',
    ': page === "targets" ? "追蹤目標達成、年度差距及各月轉介紀錄。" : "管理註冊申請、角色與據點存取權限。"',
)

s = replace(
    s,
    '<th>租期</th>',
    '<th>租期</th><th>空倉起始日</th>',
)

s = replace(
    s,
    '<td>{unit.leasePeriod || "—"}</td>',
    '<td>{unit.leasePeriod || "—"}</td><td><VacancyCell unit={unit} editable={Boolean(canWrite)} /></td>',
)

s = replace(
    s,
    'exitReason: form.get("exitReason"),',
    'exitReason: form.get("exitReason"), exitCategory: form.get("exitCategory"),',
)

s = replace(
    s,
    '{modal.type === "exit" && (',
    '''{modal.type === "exit" && (
                  <label>
                    退租原因分類
                    <select aria-label="退租原因分類" name="exitCategory" required defaultValue="">
                      <option value="" disabled>請選擇</option>
                      {exitCategories.map(c=><option key={c} value={c}>{c}</option>)}
                    </select>
                  </label>
                )}
                {modal.type === "exit" && (''',
)

s = replace(
    s,
    'event.exitReason || "未記錄"',
    '`${event.exitCategory || "未分類"}：${event.exitReason || "未記錄"}`',
)
files["src/main.tsx"] = s

s = read("src/RentalDetails.tsx")
s = replace(
    s,
    'row.exitReason || "未記錄"',
    '`${row.exitCategory || "未分類"}：${row.exitReason || "未記錄"}`',
)
files["src/RentalDetails.tsx"] = s

files["src/style.css"] = read("src/style.css") + '''
.target-panel { margin-bottom:24px; padding:24px; }
.target-panel h3 { margin-top:24px; }
'''

s = read("firestore.rules")

s = replace(
    s,
    '      match /imports/{importId} {',
    modules["rules"] + '      match /imports/{importId} {',
)

s = replace(
    s,
    'return u.code == code',
    '''return (!('vacantSince' in u)
              || u.vacantSince == null
              || (u.status == 'vacant'
                && u.vacantSince is string
                && u.vacantSince.matches('[0-9]{4}-[0-9]{2}-[0-9]{2}')))
            && u.code == code''',
)

s = replace(
    s,
    'allow create: if branchEdit(id)\n'
    '          && unlocked(id)\n'
    '          && request.resource.data.type in [',
    '''allow create: if branchEdit(id)
          && unlocked(id)
          && (
            request.resource.data.type != 'exit'
            || (
              request.resource.data.exitCategory in [
                '價格', '距離', '不再需要',
                '改租其它倉位/據點', '服務或環境', '其它'
              ]
              && request.resource.data.exitReason is string
              && request.resource.data.exitReason.size() > 0
              && request.resource.data.exitReason.size() <= 500
            )
          )
          && request.resource.data.type in [''',
)
files["firestore.rules"] = s

for name, content in files.items():
    (root / name).write_text(content, encoding="utf-8")
    print("已更新 " + name)
