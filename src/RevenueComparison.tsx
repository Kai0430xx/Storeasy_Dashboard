import "./revenue-disclosure.css";
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

function RevenueComparisonContent({
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


type RevenueProps = {
  branches: Row[];
  data: Record<string, Row>;
  month: string;
  collapsible?: boolean;
};

export default function RevenueComparison({
  collapsible = false,
  ...props
}: RevenueProps) {
  if (!collapsible) {
    return <RevenueComparisonContent {...props}/>;
  }

  return (
    <details className="panel revenue-disclosure">
      <summary>業績去年同月比較</summary>
      <div className="revenue-disclosure-body">
        <p>
          {props.month} 與 {Number(props.month.slice(0, 4)) - 1}
          {props.month.slice(4)} · KPI 實際業績金額
        </p>
        <RevenueComparisonContent {...props}/>
      </div>
    </details>
  );
}
