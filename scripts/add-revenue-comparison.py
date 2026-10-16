from pathlib import Path

root = Path(__file__).resolve().parents[1]
main = root / "src/main.tsx"
source = main.read_text(encoding="utf-8")

if 'import RevenueComparison from "./RevenueComparison";' not in source:
    anchor = '<div className="dashboard-grid">'
    if source.count(anchor) != 1:
        raise SystemExit("找不到唯一的營運總覽位置，未變更檔案")

    updated = source.replace(
        anchor,
        '<RevenueComparison branches={visible} data={data} month={month}/>\n'
        '                  ' + anchor,
        1,
    )
    updated = (
        'import RevenueComparison from "./RevenueComparison";\n' + updated
    )

    backup = main.with_name("main.tsx.before-revenue-comparison")
    if not backup.exists():
        backup.write_text(source, encoding="utf-8")
    main.write_text(updated, encoding="utf-8")

(root / "src/RevenueComparison.tsx").write_text(r'''
import { revenueComparison } from './revenue-comparison.js';
import { taipeiDate } from './domain.js';

type Row = Record<string, any>;

const money = (n: number | null) =>
  n === null
    ? '無資料'
    : `NT$ ${n.toLocaleString('zh-TW', {maximumFractionDigits: 2})}`;

const signedMoney = (n: number | null) =>
  n === null
    ? '無法比較'
    : `${n > 0 ? '+' : n < 0 ? '−' : ''}${money(Math.abs(n))}`;

const percent = (r: Row) =>
  r.difference === null
    ? '無法比較'
    : r.previous === 0
      ? '去年為 0，不計算增減率'
      : `${r.percent > 0 ? '+' : ''}${r.percent.toFixed(1)}%`;

export default function RevenueComparison({
  branches, data, month,
}: {
  branches: Row[];
  data: Record<string, Row>;
  month: string;
}) {
  const {rows, total, previousMonth} =
    revenueComparison(branches, data, month);
  const loading = branches.some(
    b => !Array.isArray(data[b.id]?.months),
  );

  return (
    <section
      className="panel target-panel"
      aria-label="業績去年同月比較"
    >
      <div className="panel-heading">
        <div>
          <h2>業績去年同月比較</h2>
          <p>
            {month} 與 {previousMonth} · KPI 實際業績金額
          </p>
        </div>
      </div>

      {loading ? (
        <p role="status">載入業績資料中…</p>
      ) : (
        <>
          <p>
            可比較據點 {total.count}／{branches.length}；
            合計僅納入兩年都有業績的據點。
          </p>

          {month === taipeiDate().slice(0, 7) && (
            <p className="hint">
              當月尚未結束；目前匯入業績與去年整月比較，
              非同期累計比較。
            </p>
          )}

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>據點</th>
                  <th>本期業績</th>
                  <th>去年同月業績</th>
                  <th>增減金額</th>
                  <th>增減率</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th>可比較據點合計</th>
                  <td>{money(total.current)}</td>
                  <td>{money(total.previous)}</td>
                  <td>{signedMoney(total.difference)}</td>
                  <td>{percent(total)}</td>
                </tr>
                {rows.map((r: Row) => (
                  <tr key={r.id}>
                    <td>{r.name}</td>
                    <td>{money(r.current)}</td>
                    <td>
                      {r.previous === null
                        ? '無去年同期資料'
                        : money(r.previous)}
                    </td>
                    <td>{signedMoney(r.difference)}</td>
                    <td>{percent(r)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="hint">
            增減率＝（本期業績－去年同月業績）÷去年同月業績。
            資料來自已匯入 KPI，不以月租或業績完成率推算。
          </p>
        </>
      )}
    </section>
  );
}
'''.lstrip('\n'), encoding="utf-8")

(root / "src/revenue-comparison.js").write_text(r'''
const valid = n =>
  typeof n === 'number' && Number.isFinite(n) && n >= 0;

function comparison(current, previous) {
  const difference =
    current !== null && previous !== null
      ? current - previous
      : null;

  return {
    current,
    previous,
    difference,
    percent:
      difference !== null && previous > 0
        ? difference / previous * 100
        : null,
  };
}

export function revenueComparison(branches, data, month) {
  const previousMonth =
    `${Number(month.slice(0, 4)) - 1}${month.slice(4)}`;

  const amount = (id, period) => {
    const saved = data[id]?.months?.find(
      m => (m.id || m.month) === period,
    );
    const n =
      saved?.source === 'import'
        ? saved.kpiMetrics?.revenue
        : null;

    return valid(n) ? n : null;
  };

  const rows = branches.map(b => ({
    id: b.id,
    name: b.name,
    ...comparison(
      amount(b.id, month),
      amount(b.id, previousMonth),
    ),
  }));

  const matched = rows.filter(r => r.difference !== null);

  const total = {
    ...comparison(
      matched.length
        ? matched.reduce((sum, r) => sum + r.current, 0)
        : null,
      matched.length
        ? matched.reduce((sum, r) => sum + r.previous, 0)
        : null,
    ),
    count: matched.length,
  };

  return {rows, total, previousMonth};
}
'''.lstrip('\n'), encoding="utf-8")

print("已加入業績去年同月比較")
