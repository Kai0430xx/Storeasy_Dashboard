
import React from "react";
import { rentalDetails } from "./lease-term.js";

type Row = Record<string, any>;

export default function RentalDetails({
  type, month, events, units, total,
}: {
  type: string;
  month: string;
  events: Row[];
  units: Row[];
  total: number | null;
}) {
  const result = rentalDetails(events, units, type, month);
  const rows: Row[] = result.rows;
  const counts: Row = result.counts;
  const names: Row = {
    new: "新承租",
    renew: "續約",
    exit: "退租",
  };

  return (
    <>
      <h2>{names[type]}明細 · {month}</h2>
      <p>
        統計總筆數：{total ?? "無資料"}；
        可查明細：{rows.length} 筆。
      </p>

      {type !== "exit" && (
        <div className="preview-counts rental-summary">
          {Object.entries({
            monthly: "月租",
            quarterly: "季租",
            halfYear: "半年租",
            yearly: "年租",
            other: "其他租期",
            unknown: "租期未記錄",
          }).map(([key, label]) => (
            <span key={key}>
              {label} <b>{counts[key]} 筆</b>
            </span>
          ))}
        </div>
      )}

      <p className="hint">
        按起訖日期辨識 1、3、6、12 個月租期。
        KPI 匯入只有彙總，未提供倉位明細；
        舊異動未記錄租期時不使用現況推算歷史分類。
      </p>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>日期</th>
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
              <tr key={`${row.branchId}/${row.id}`}>
                <td>{row.date}</td>
                <td>
                  {row.code}
                  <small className="table-sub">
                    {row.branchName}
                  </small>
                </td>
                <td>{row.details.dimensions || "—"}</td>
                <td>{row.details.volume ?? "—"}</td>
                <td>
                  {row.details.price == null
                    ? "—"
                    : `NT$ ${Number(row.details.price).toLocaleString()}`}
                </td>
                <td>
                  {(type === "exit"
                    ? row.previousLease?.leasePeriod
                    : row.details.leasePeriod) || "未記錄"}
                </td>
                <td>{row.details.note || "—"}</td>
                <td>
                  {row.historical ? "異動時" : "現況／舊紀錄"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {!rows.length && (
          <p>此月份沒有可查詢的倉位異動明細。</p>
        )}
      </div>
    </>
  );
}
