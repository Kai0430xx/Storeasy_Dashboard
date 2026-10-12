import React, { useState } from "react";

type Row = Record<string, any>;

export default function ImportSources({
  branches,
  data,
  canWrite,
  busy,
  onRemove,
}: {
  branches: Row[];
  data: Record<string, any>;
  canWrite: boolean;
  busy: boolean;
  onRemove: (payload: Row) => void;
}) {
  const [pending, setPending] = useState<Row | null>(null);

  const rows = branches.flatMap(branch => {
    const months: Row[] = data[branch.id]?.months || [];
    const files = new Set<string>();
    const items: Row[] = [];

    for (
      const month of months.filter(
        item => item.source === "import"
      )
    ) {
      for (
        const filename of [
          month.sourceFile,
          month.amountSourceFile,
        ]
      ) {
        if (
          filename &&
          filename !== "舊資料未記錄檔名"
        ) {
          files.add(filename);
        }
      }
    }

    if (branch.inventorySource || branch.inventoryDate) {
      items.push({
        branchId: branch.id,
        branchName: branch.name,
        kind: "inventory",
        sourceId: branch.inventorySource?.id || "legacy",
        name:
          `總倉：${branch.inventorySource?.total || "舊資料未記錄檔名"}` +
          `／空倉：${branch.inventorySource?.vacant || "舊資料未記錄檔名"}`,
        detail: `現況盤點日期：${branch.inventoryDate || "—"}`,
      });
    }

    for (const filename of files) {
      const used = months.filter(
        month =>
          month.source === "import" &&
          (
            month.sourceFile === filename ||
            month.amountSourceFile === filename
          )
      );

      const countMonths = used
        .filter(month => month.sourceFile === filename)
        .map(month => month.id)
        .sort()
        .join("、");

      const amountMonths = used
        .filter(month => month.amountSourceFile === filename)
        .map(month => month.id)
        .sort()
        .join("、");

      items.push({
        branchId: branch.id,
        branchName: branch.name,
        kind: "kpi",
        filename,
        name: filename,
        detail:
          `數量：${countMonths || "—"}` +
          `；金額：${amountMonths || "—"}`,
      });
    }

    return items;
  });

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>目前採用的匯入來源</h2>
          <p>
            顯示檔名與採用範圍；舊資料未記錄檔名，
            重新匯入後才會顯示。
          </p>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>據點／類型</th>
              <th>來源檔案</th>
              <th>採用範圍</th>
              {canWrite && <th>操作</th>}
            </tr>
          </thead>

          <tbody>
            {rows.map((row, index) => (
              <tr key={`${row.branchId}-${row.kind}-${index}`}>
                <td>
                  {row.branchName}
                  <small className="table-sub">
                    {row.kind === "inventory" ? "總倉＋空倉" : "KPI"}
                  </small>
                </td>
                <td>{row.name}</td>
                <td>{row.detail}</td>
                {canWrite && (
                  <td>
                    <button
                      className="text-button danger"
                      disabled={busy}
                      onClick={() => setPending(row)}
                    >
                      刪除匯入資料
                    </button>
                  </td>
                )}
              </tr>
            ))}

            {!rows.length && (
              <tr>
                <td colSpan={canWrite ? 4 : 3}>
                  尚無已記錄的來源檔案。
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {pending && (
        <div className="modal-backdrop">
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label="刪除匯入資料"
          >
            <h2>刪除匯入資料</h2>
            <p>{pending.branchName}：{pending.name}</p>

            <p>
              {pending.kind === "inventory"
                ? "將清空此據點目前的倉位現況（含後續手動修改），總倉與空倉資料一起移除，不會自動切回上一份檔案。歷史 KPI、承租異動與價格紀錄保留，可重新匯入建立現況。"
                : "將刪除採用此檔案的整月份 KPI 統計，包含該月份金額及數量，歷史比較將顯示無資料。即時承租異動不會刪除，可重新匯入。"}
            </p>

            <button
              className="primary danger"
              disabled={busy}
              onClick={() => {
                onRemove(pending);
                setPending(null);
              }}
            >
              確認刪除匯入資料
            </button>
            {" "}
            <button
              className="secondary"
              disabled={busy}
              onClick={() => setPending(null)}
            >
              取消
            </button>
          </section>
        </div>
      )}
    </section>
  );
}
