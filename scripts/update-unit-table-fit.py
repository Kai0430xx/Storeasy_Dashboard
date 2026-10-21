from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
main = root / "src/main.tsx"
manual = root / "src/manual-content.ts"
text = main.read_text(encoding="utf-8")

if 'className="unit-note-preview"' not in text:
    pattern = (
        r'(<td\s+data-label="備註"\s*>)\s*'
        r'\{(\w+)\.note\s*\|\|\s*["\']—["\']\}\s*(</td>)'
    )

    if len(re.findall(pattern, text)) != 1:
        raise SystemExit("找不到唯一的倉位備註欄，尚未修改任何檔案。")

    text = re.sub(
        pattern,
        lambda m: (
            m[1]
            + '<span className="unit-note-preview">{'
            + m[2]
            + '.note || "—"}</span>'
            + m[3]
        ),
        text,
    )

if "import './unit-table-fit.css';" not in text:
    text += "\nimport './unit-table-fit.css';\n"

styles = """/* unit-table-fit-v1 */
.table-wrap:has(> table.mobile-unit-table) {
  min-width: 0;
  max-width: 100%;
}
table.mobile-unit-table {
  width: 100%;
  min-width: 0;
  table-layout: fixed;
  white-space: normal;
}
.mobile-unit-table th,
.mobile-unit-table td {
  box-sizing: border-box;
  min-width: 0;
  white-space: normal;
  overflow-wrap: anywhere;
}
.mobile-unit-table .unit-note-preview {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.5;
  max-height: 3em;
}
.mobile-unit-table .row-actions {
  flex-wrap: wrap;
  min-width: 0;
}
.mobile-unit-table .row-actions button {
  max-width: 100%;
  white-space: normal;
}
.mobile-unit-table .badge {
  max-width: 100%;
  white-space: normal;
  overflow-wrap: anywhere;
}
@media (min-width: 761px) {
  .mobile-unit-table th,
  .mobile-unit-table td {
    padding: 14px 8px;
  }
  .mobile-unit-table th:nth-child(1) { width: 12%; }
  .mobile-unit-table th:nth-child(2) { width: 13%; }
  .mobile-unit-table th:nth-child(3) { width: 6%; }
  .mobile-unit-table th:nth-child(4) { width: 10%; }
  .mobile-unit-table th:nth-child(5) { width: 10%; }
  .mobile-unit-table th:nth-child(6) { width: 17%; }

  .mobile-unit-table:has(td[data-label="操作"]) th:last-child {
    width: 14%;
  }
  .mobile-unit-table:has(td[data-label="空倉起始日"]) th:nth-child(7) {
    width: 10%;
  }
}
"""

manual_text = manual.read_text(encoding="utf-8")

if "// unit-table-fit-v1-manual" not in manual_text:
    manual_text += """
// unit-table-fit-v1-manual
manualPages.find(p => p.id === 'units')?.topics.push({
  title: '倉位清單欄寬與備註顯示',
  steps: [
    '倉位清單依畫面寬度配置欄位，長尺寸會換行，操作按鈕可換行，手機維持卡片排列。',
    '備註最多顯示兩行，超出以省略號收尾。需要查看完整內容時，有編輯權限者可開啟該倉位的「編輯」。'
  ],
  result: '備註僅縮短清單上的顯示，不會截斷或修改原始資料；長文字不會撐寬倉位清單。'
});
"""

main.write_text(text, encoding="utf-8")
(root / "src/unit-table-fit.css").write_text(styles, encoding="utf-8")
manual.write_text(manual_text, encoding="utf-8")

print("已調整倉位清單欄寬、備註兩行省略，並更新操作手冊。")
