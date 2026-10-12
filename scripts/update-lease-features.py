from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
files = {}


def read(name):
    return (root / name).read_text(encoding="utf-8")


def replace(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError("找不到唯一替換位置：" + old[:100])
    return text.replace(old, new, 1)


def sub(text, pattern, new):
    text, count = re.subn(
        pattern,
        lambda m: new,
        text,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError("找不到替換位置：" + pattern[:100])
    return text


if 'from "./lease.js"' in read("src/main.tsx"):
    print("租期功能已套用，不重複修改。")
    raise SystemExit(0)

NEW_FILES = {}

NEW_FILES["src/lease.js"] = r'''
import { validDate, taipeiDate } from "./domain.js";

export function parseLease(value) {
  const text = String(value ?? "").normalize("NFKC").trim();
  if (!text) {
    return { leasePeriod: "", leaseStart: null, leaseEnd: null };
  }

  const match = text.match(
    /^(\d{4})[\/.-](\d{1,2})[\/.-](\d{1,2})\s*(?:-|—|–|~|至)\s*(\d{4})[\/.-](\d{1,2})[\/.-](\d{1,2})$/
  );

  if (!match) {
    throw new Error(
      "租期格式不正確，請使用 2026/10/08－2027/04/07"
    );
  }

  const date = offset =>
    `${match[offset]}-${match[offset + 1].padStart(2, "0")}-${match[offset + 2].padStart(2, "0")}`;

  const leaseStart = date(1);
  const leaseEnd = date(4);

  if (
    !validDate(leaseStart) ||
    !validDate(leaseEnd) ||
    leaseStart > leaseEnd
  ) {
    throw new Error("租期日期不存在，或結束日早於開始日");
  }

  return {
    leasePeriod:
      `${leaseStart.replace(/-/g, "/")}－${leaseEnd.replace(/-/g, "/")}`,
    leaseStart,
    leaseEnd,
  };
}

export function leaseStatus(unit, date = taipeiDate()) {
  if (unit.missing) {
    return {
      key: "missing",
      label: "清單中消失",
      color: "warning",
    };
  }

  if (unit.status !== "rented") {
    return { key: "vacant", label: "空倉", color: "green" };
  }

  if (!unit.leaseEnd) {
    return {
      key: "unknown",
      label: "已出租（租期未提供）",
      color: "blue",
    };
  }

  if (unit.leaseEnd < date) {
    return { key: "overdue", label: "已逾期", color: "red" };
  }

  if (unit.leaseStart > date) {
    return { key: "upcoming", label: "尚未起租", color: "blue" };
  }

  const days = Math.round(
    (
      Date.parse(`${unit.leaseEnd}T00:00:00Z`) -
      Date.parse(`${date}T00:00:00Z`)
    ) / 86400000
  );

  return days <= 14
    ? { key: "expiring", label: "即將到期", color: "warning" }
    : { key: "active", label: "租期內", color: "blue" };
}
'''

NEW_FILES["src/unit-view.js"] = r'''
export function compareUnits(a, b, sortBy = "code") {
  const code = String(a.code || "").localeCompare(
    String(b.code || ""),
    "zh-Hant",
    { numeric: true }
  );

  const volume = Number(a.volume || 0) - Number(b.volume || 0);

  return (sortBy === "volume" ? volume || code : code) ||
    String(a.branchName || "").localeCompare(
      String(b.branchName || ""),
      "zh-Hant",
      { numeric: true }
    );
}

export function activityUsageDetails(events, units, activity, month) {
  const lookup = new Map(
    units.map(unit => [`${unit.branchId}/${unit.code}`, unit])
  );

  return events
    .filter(event =>
      !event.voided &&
      event.month === month &&
      event.branchId === activity.branchId &&
      event.activities?.some(item => item.id === activity.id)
    )
    .map(event => {
      const current = lookup.get(
        `${event.branchId}/${event.code}`
      );
      const snapshot = event.unitSnapshot;

      return {
        ...event,
        details: snapshot || current || event.priceSnapshot || {},
        historical: !!snapshot,
      };
    })
    .sort(
      (a, b) =>
        b.date.localeCompare(a.date) || compareUnits(a, b)
    );
}
'''

NEW_FILES["src/ActivityUsage.tsx"] = r'''
import React from "react";
import { activityUsageDetails } from "./unit-view.js";

type Row = Record<string, any>;

export default function ActivityUsage({
  activity, month, events, units,
}: {
  activity: Row;
  month: string;
  events: Row[];
  units: Row[];
}) {
  const rows: Row[] = activityUsageDetails(
    events, units, activity, month
  );

  return (
    <>
      <h2>{activity.name} · 使用明細</h2>
      <p>
        {activity.branchName}／{month}：
        {rows.length} 次使用，
        {new Set(rows.map(row => row.code)).size} 個倉位。
      </p>
      <p className="hint">
        新紀錄顯示活動使用時的倉位資料；
        舊紀錄未保存完整資料時，顯示可取得的現況。
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>使用日期</th>
              <th>倉位／據點</th>
              <th>尺寸</th>
              <th>材積</th>
              <th>月租</th>
              <th>租期</th>
              <th>備註</th>
              <th>資料時間</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(row => (
              <tr key={row.id}>
                <td>{row.date}</td>
                <td>
                  {row.code}
                  <small className="table-sub">
                    {activity.branchName}
                  </small>
                </td>
                <td>{row.details.dimensions || "—"}</td>
                <td>{row.details.volume ?? "—"}</td>
                <td>
                  {row.details.price == null
                    ? "—"
                    : `NT$ ${Number(row.details.price).toLocaleString()}`}
                </td>
                <td>{row.details.leasePeriod || "未提供"}</td>
                <td>{row.details.note || "—"}</td>
                <td>
                  {row.historical ? "使用時" : "現況／舊紀錄"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length && <p>本月尚無使用紀錄。</p>}
      </div>
    </>
  );
}
'''

files.update(NEW_FILES)

s = read("src/domain.js")
s = 'import { parseLease } from "./lease.js";\n' + s
s = replace(
    s,
    "export function normalizeUnits(rows) {",
    "/** @returns {Array<{code:string,dimensions:string,volume:number,price:number,unitPrice:number,note:string,leasePeriod?:string,leaseStart?:string|null,leaseEnd?:string|null}>} */\nexport function normalizeUnits(rows) {",
)
s = replace(
    s,
    "      code,\n      dimensions:",
    '      code,\n      ...("leasePeriod" in row ? parseLease(row.leasePeriod) : {}),\n      dimensions:',
)
files["src/domain.js"] = s

s = read("src/imports.js")
s = 'import { parseLease } from "./lease.js";\n' + s
s = replace(
    s,
    "export function parseUnits(",
    "/** @param {{requirePrice?: boolean, requireLease?: boolean}} [options] */\nexport function parseUnits(",
)
s = replace(
    s,
    "  const priceIndex = column([",
    '  const leaseIndex = column(["租期"]);\n  if (options.requireLease && leaseIndex < 0) throw new Error("缺少「租期」欄位；空倉請保留此欄並留空");\n  const priceIndex = column([',
)
s = replace(
    s,
    "      code,\n      dimensions:",
    """      code,
      ...(leaseIndex < 0 ? {} : (() => {
        try { return parseLease(row[leaseIndex]); }
        catch (error) { throw new Error(`倉位 ${code}：${error.message}`); }
      })()),
      dimensions:""",
)
files["src/imports.js"] = s

s = read("src/import-actions.ts")
s = replace(s, "        vacant: filename(data.vacantFile),\n", "")
files["src/import-actions.ts"] = s

s = read("src/api.ts")
s = 'import { parseLease } from "./lease.js";\n' + s

start = s.index('    case "recordEvent":')
end = s.index('    case "voidEvent":', start)
block = s[start:end]
block = replace(
    block,
    "        const delta =",
    '''        const lease = parseLease(type === "exit" ? "" : data.leasePeriod);
        if (type !== "exit" && !lease.leasePeriod) throw new Error("承租與續約必須填寫租期");
        const previousLease = {
          leasePeriod: unit.leasePeriod || "",
          leaseStart: unit.leaseStart || null,
          leaseEnd: unit.leaseEnd || null,
        };
        const delta =''',
)
block = replace(
    block,
    "transaction.update(unitDoc, {\n          status:",
    "transaction.update(unitDoc, {\n          ...lease,\n          status:",
)
block = replace(
    block,
    "          priceSnapshot: priceSnapshot(unit, date),",
    """          priceSnapshot: priceSnapshot(unit, date),
          unitSnapshot: {
            dimensions: unit.dimensions,
            volume: unit.volume,
            price: priceSnapshot(unit, date).price,
            note: unit.note,
            ...lease,
          },
          previousLease,""",
)
s = s[:start] + block + s[end:]

start = s.index('    case "voidEvent":')
end = s.index('    case "saveUnit":', start)
block = replace(
    s[start:end],
    "transaction.update(unitDoc, {\n          status:",
    'transaction.update(unitDoc, {\n          ...(event.previousLease || { leasePeriod: "", leaseStart: null, leaseEnd: null }),\n          status:',
)
s = s[:start] + block + s[end:]

start = s.index('    case "saveUnit":')
end = s.index('    case "removeImport":', start)
block = replace(
    s[start:end],
    "          transaction.set(\n            unitDoc,",
    '''          if (unitSnapshot.data()?.status === "rented" && "leasePeriod" in data && !unit.leasePeriod)
            throw new Error("已出租倉位必須填寫租期；若已退租請使用退租操作");
          if ((!unitSnapshot.exists() || unitSnapshot.data()?.status === "vacant") && unit.leasePeriod)
            throw new Error("空倉請先登記承租，再填寫租期");
          transaction.set(
            unitDoc,''',
)
s = s[:start] + block + s[end:]

s = sub(
    s,
    r"const vacant = new Set<string>\(\s*data\.vacantCodes\s*\);",
    '''const vacant = new Set<string>(units.filter(unit => !unit.leasePeriod).map(unit => unit.code));
      if (data.units.some((unit: any) => typeof unit.leasePeriod !== "string"))
        throw new Error("請使用含「租期」欄的單一倉位表重新匯入");
      if (data.vacantCodes.some((code: string) => !vacant.has(code)))
        throw new Error("租期與空倉判定不一致");''',
)
files["src/api.ts"] = s

s = read("src/main.tsx")
s = (
    'import { leaseStatus } from "./lease.js";\n'
    'import { compareUnits } from "./unit-view.js";\n'
    'import ActivityUsage from "./ActivityUsage";\n'
) + s
s = replace(
    s,
    "function App() {",
    '''function App() {
  const [unitSort, setUnitSort] = useState("code");
  const [currentDate, setCurrentDate] = useState(today());
  useEffect(() => {
    const timer = window.setInterval(() => setCurrentDate(today()), 60000);
    return () => window.clearInterval(timer);
  }, []);''',
)
s = replace(
    s,
    'page === "units" || page === "imports"',
    'page === "units" || page === "imports" || page === "activities"',
)

start = s.index('{page === "units" && (')
end = s.index('{page === "activities" && (', start)
block = s[start:end]
block = replace(
    block,
    "<th>倉位／據點</th>\n                            <th>尺寸</th>\n                            <th>材積</th>",
    '''<th aria-sort={unitSort === "code" ? "ascending" : "none"}><button className="text-button" aria-label="倉位／據點" onClick={() => setUnitSort("code")}>倉位／據點{unitSort === "code" ? " ↑" : ""}</button></th>
                            <th>尺寸</th>
                            <th aria-sort={unitSort === "volume" ? "ascending" : "none"}><button className="text-button" aria-label="材積" onClick={() => setUnitSort("volume")}>材積{unitSort === "volume" ? " ↑" : ""}</button></th>''',
)
block = replace(
    block,
    "<th>狀態</th>",
    "<th>狀態</th><th>租期</th>",
)
block = replace(
    block,
    "(status === unit.status && !unit.missing)",
    "(status === unit.status && !unit.missing) || status === leaseStatus(unit, currentDate).key",
)
block = replace(
    block,
    "a.code.localeCompare(b.code)",
    "compareUnits(a, b, unitSort)",
)
block = sub(
    block,
    r"<span className=\{`badge \$\{\s*unit\.missing.*?</span>",
    '<span className={`badge ${leaseStatus(unit, currentDate).color}`}>{leaseStatus(unit, currentDate).label}</span>',
)
block = replace(
    block,
    '<td>{unit.note || "—"}</td>',
    '<td>{unit.leasePeriod || "—"}</td>\n                                <td>{unit.note || "—"}</td>',
)
block = replace(
    block,
    '<option value="rented">已出租</option>',
    '''<option value="rented">全部已出租</option>
                      <option value="active">租期內</option>
                      <option value="expiring">即將到期</option>
                      <option value="overdue">已逾期</option>
                      <option value="upcoming">尚未起租</option>
                      <option value="unknown">租期未提供</option>''',
)
s = s[:start] + block + s[end:]

start = s.index('<div className="activity-bottom">')
end = s.index("{canWrite && (", start)
block = s[start:end]
block = replace(
    block,
    "<span>",
    '<button className="text-button" onClick={() => setModal({ kind: "activityUsage", activity, month })}>',
)
block = replace(block, "</span>", "</button>")
s = s[:start] + block + s[end:]

s = sub(
    s,
    r'\["inventory", "kpi"\]\.includes\(modal\.kind\)\s*\? "wide"',
    '["inventory", "kpi", "activityUsage"].includes(modal.kind) ? "wide"',
)
s = replace(
    s,
    'activity: "活動設定",',
    'activity: "活動設定",\n                      activityUsage: "活動使用明細",',
)
s = replace(
    s,
    '{modal.kind === "event" && (',
    '''{modal.kind === "activityUsage" && (
              <ActivityUsage activity={modal.activity} month={modal.month} events={events} units={units} />
            )}
            {modal.kind === "event" && (''',
)
s = replace(
    s,
    'activityIds: form.getAll("activity"),',
    'activityIds: form.getAll("activity"),\n                      leasePeriod: form.get("leasePeriod"),',
)
s = replace(
    s,
    '{modal.type !== "exit" && (\n                  <fieldset>',
    '''{modal.type !== "exit" && (
                  <label>
                    {modal.type === "renew" ? "新的租期" : "租期"}
                    <input aria-label={modal.type === "renew" ? "新的租期" : "租期"} name="leasePeriod" required placeholder="2026/10/08－2027/04/07" autoComplete="off" />
                    <small className="hint">請貼上完整起訖日期，例如 2026/10/08－2027/04/07。</small>
                  </label>
                )}
                {modal.type !== "exit" && (
                  <fieldset>''',
)

start = s.index('{modal.kind === "unitEdit" && (')
end = s.index('{modal.kind === "void" && (', start)
block = sub(
    s[start:end],
    r"<label>\s*備註",
    '''{modal.status === "rented" && (
                  <label>租期<input name="leasePeriod" required defaultValue={modal.leasePeriod || ""} placeholder="2026/10/08－2027/04/07" /></label>
                )}
                <label>
                  備註''',
)
s = s[:start] + block + s[end:]

start = s.index(
    '            if (kind === "inventory") {',
    s.index("function ImportForm"),
)
end = s.index("            } else {", start)
s = s[:start] + '''            if (kind === "inventory") {
              const all = parseUnits(
                await workbook(await (form.get("all") as File).arrayBuffer()),
                undefined,
                { requirePrice: true, requireLease: true },
              );
              const vacant = all.filter((unit: Row) => !unit.leasePeriod).map((unit: Row) => unit.code);
              const codes = new Set(all.map((unit: Row) => unit.code));
              setPreview({
                units: all,
                totalFile: (form.get("all") as File).name,
                vacantCodes: vacant,
                effectiveDate: form.get("date"),
                missing: units.filter(unit => !unit.archived && !codes.has(unit.code)).map(unit => unit.code),
              });
''' + s[end:]

s = sub(s, r"<label>\s*空倉 Excel.*?</label>", "")
s = s.replace("總倉 Excel", "倉位 Excel")
s = s.replace(
    "尚無倉位資料，請先匯入總倉與空倉清單。",
    "尚無倉位資料，請先匯入含租期欄位的倉位表。",
)
s = sub(
    s,
    r"同時選擇總倉與空倉\s*Excel。.*?匯入前先預覽比對結果。",
    "只需上傳一份倉位 Excel。有租期代表已出租，租期空白代表空倉。到期前 14 天標示即將到期，逾期仍計入已出租，直到登記退租。",
)
s = s.replace("月租、備註", "月租、備註、租期")
files["src/main.tsx"] = s

s = read("src/style.css")
files["src/style.css"] = (
    s + "\n.badge.red { background: #fff0ec; color: #b42318; }\n"
)

s = read("src/ImportSources.tsx")
s = replace(s, '"總倉＋空倉"', '"倉位表"')
s = s.replace("總倉與空倉資料一起移除", "倉位表資料移除")

if "name: `總倉：" in s:
    s = sub(
        s,
        r"name:\s*`總倉：.*?空倉：.*?`,",
        '''name: b.inventorySource?.vacant
        ? `總倉：${b.inventorySource.total}／空倉：${b.inventorySource.vacant}`
        : `倉位：${b.inventorySource?.total || "舊資料未記錄檔名"}`,''',
    )
else:
    s = sub(
        s,
        r"name:\s*`總倉：.*?`\s*\+\s*`／空倉：.*?`,",
        '''name: branch.inventorySource?.vacant
        ? `總倉：${branch.inventorySource.total}／空倉：${branch.inventorySource.vacant}`
        : `倉位：${branch.inventorySource?.total || "舊資料未記錄檔名"}`,''',
    )

files["src/ImportSources.tsx"] = s

for name, content in files.items():
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print("已更新 " + name)
