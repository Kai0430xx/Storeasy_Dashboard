
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
      <h2>{activity.name} · 使用明細</h2><p>活動分類：<strong>{activity.category || "未分類"}</strong></p>
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
