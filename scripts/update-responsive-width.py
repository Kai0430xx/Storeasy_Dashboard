from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
main = root / "src/main.tsx"
waiting = root / "src/WaitingList.tsx"
manual = root / "src/manual-content.ts"

s = main.read_text(encoding="utf-8")
w = waiting.read_text(encoding="utf-8")

if 'className="waiting-date-value"' not in w:
    pattern = r'(<td data-label="登記日期">)([\s\S]*?)(</td>)'

    if len(re.findall(pattern, w)) != 1:
        raise SystemExit("找不到唯一的候補登記日期欄，尚未修改檔案。")

    w = re.sub(
        pattern,
        lambda m: (
            m[1]
            + '<span className="waiting-date-value">'
            + m[2]
            + "</span>"
            + m[3]
        ),
        w,
        count=1,
    )

if "import './responsive-width.css';" not in s:
    s += "\nimport './responsive-width.css';\n"

css = """/* responsive-width-v1 */
.content {
  width:100%;
  box-sizing:border-box;
  padding-inline:clamp(12px,2.2vw,38px);
}
.page-title { flex-wrap:wrap; }
.page-title > div { min-width:0; }
.page-title .filters {
  max-width:100%;
  flex-wrap:wrap;
}
.toolbar { flex-wrap:wrap; gap:12px; }
.toolbar > * { min-width:0; max-width:100%; }
.modal {
  box-sizing:border-box;
  max-width:calc(100vw - 24px);
}
.activity-grid {
  grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));
}
.waiting-summary {
  container-type:inline-size;
  container-name:waiting-list;
}
.waiting-summary .waiting-list-table {
  width:100%;
  min-width:0;
  table-layout:fixed;
}
.waiting-summary .waiting-list-table th:nth-child(1) {
  width:154px;
}
.waiting-summary .waiting-list-table th:nth-child(2) {
  width:14%;
}
.waiting-summary .waiting-list-table th:nth-child(3) {
  width:auto;
}
.waiting-summary .waiting-list-table th:nth-child(4),
.waiting-summary .waiting-list-table th:nth-child(5) {
  width:8%;
}
.waiting-summary .waiting-list-table th:nth-child(6),
.waiting-summary .waiting-list-table th:nth-child(7) {
  width:126px;
}
.waiting-summary .waiting-list-table th:nth-child(8),
.waiting-summary .waiting-list-table th:nth-child(9) {
  width:88px;
}
.waiting-summary .waiting-date-value {
  display:inline-flex;
  align-items:center;
  white-space:nowrap;
  gap:8px;
  overflow-wrap:normal;
  word-break:normal;
  max-width:100%;
}
.waiting-summary .waiting-date-value .waiting-read-check {
  margin:0;
  flex-shrink:0;
}
.waiting-summary .waiting-list-table td { min-width:0; }

@container waiting-list (max-width:1250px) {
  .waiting-summary .waiting-list-table thead {
    display:none;
  }
  .waiting-summary .waiting-list-table,
  .waiting-summary .waiting-list-table tbody {
    display:block;
    width:100%;
  }
  .waiting-summary .waiting-list-table tr {
    display:grid;
    grid-template-columns:minmax(0,1fr) minmax(132px,1fr);
    gap:14px 12px;
    padding:14px;
    border-bottom:1px solid #dae3ed;
  }
  .waiting-summary .waiting-list-table td {
    display:block;
    min-width:0;
    width:auto;
    max-width:100%;
    padding:0;
    border:0;
    white-space:normal;
    overflow-wrap:anywhere;
  }
  .waiting-summary .waiting-list-table td::before {
    content:attr(data-label);
    display:block;
    color:#718099;
    font-size:12px;
    margin-bottom:5px;
  }
  .waiting-summary .waiting-list-table td[data-label="姓名"] {
    grid-column:1;
    grid-row:1;
  }
  .waiting-summary .waiting-list-table td[data-label="登記日期"] {
    grid-column:2;
    grid-row:1;
    text-align:right;
  }
  .waiting-summary .waiting-list-table td[data-label="候補據點"] {
    grid-column:1/-1;
    grid-row:2;
  }
  .waiting-summary .waiting-date-value {
    font-size:14px;
  }
}
"""

m = manual.read_text(encoding="utf-8")
if "// responsive-width-v1-manual" not in m:
    m += """
// responsive-width-v1-manual
manualPages.find(p => p.id === 'dashboard')?.topics.push({
 title:'依視窗寬度自動調整排版',
 steps:['縮放瀏覽器或調整視窗大小時，頁面留白、篩選列、工具列與活動卡片會依可用寬度調整；彈出視窗限制在畫面內。'],
 result:'不需依電腦手動設定版型，不會改變資料、權限或篩選結果。'
});
manualPages.find(p => p.id === 'waiting')?.topics.push({
 title:'候補清單自動切換表格與卡片',
 steps:[
  '清單可用寬度足夠時使用表格；不足時自動切換卡片，包含小螢幕電腦及放大後的視窗。',
  '日期和前方勾選框保持同一行；卡片中姓名在左、日期在右，候補據點獨立一排。'
 ],
 result:'仍可勾選已讀、開啟候補及查看配對；只調整顯示排版。'
});
"""

for p, text in [
    (main, s),
    (waiting, w),
    (manual, m),
    (root / "src/responsive-width.css", css),
]:
    p.write_text(text, encoding="utf-8")

print("已加入依可用寬度調整版型，並修正候補日期擠壓。")
