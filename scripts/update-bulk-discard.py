from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
page = root / "src/BulkUnits.tsx"
css = root / "src/bulk-units.css"
manual = root / "src/manual-content.ts"

text = page.read_text(encoding="utf-8")

if "function discardDraft()" not in text:
    anchor = " function close(){"
    pattern = (
        r"(\{rows\.length\s*===\s*success\s*\?\s*"
        r"'完成並返回'\s*:\s*'關閉並保留清單'\}\s*</button>)"
    )
    footer = re.search(pattern, text)

    if text.count(anchor) != 1 or len(re.findall(pattern, text)) != 1:
        raise SystemExit(
            "批次頁面版本不同，尚未修改任何檔案，請提供最新 BulkUnits.tsx。"
        )

    function = """ function discardDraft(){
  if(busy)return;
  if(!window.confirm('確定不保留本次清單並返回？尚未送出的資料將清除；已成功送出的異動會保留，不會撤銷。'))return;
  try{sessionStorage.removeItem(key);}catch{}
  setDraft(null);setChecked([]);setOpen(false);setError('');setPhase('edit');
 }
"""

    text = text.replace(anchor, function + anchor, 1)

    button = """{rows.length!==success&&<button className="secondary" disabled={busy} onClick={discardDraft}>不保留清單並返回</button>}"""

    text = text.replace(
        footer.group(0),
        footer.group(0) + button,
        1,
    )

styles = """
/* bulk-header-v2 */
.modal.bulk-unit-modal > .modal-heading {
  gap: 12px;
  padding: 12px 16px;
}
.modal.bulk-unit-modal > .modal-heading h2 {
  flex: 1 1 auto;
  min-width: 0;
}
.modal.bulk-unit-modal > .modal-heading > button {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: auto;
  min-width: max-content;
  height: auto;
  min-height: 44px;
  padding: 8px 12px;
  font-size: 16px;
  line-height: 1.5;
  white-space: nowrap;
  overflow-wrap: normal;
  word-break: normal;
}
"""

css_text = css.read_text(encoding="utf-8")
if "/* bulk-header-v2 */" not in css_text:
    css_text += "\n" + styles

manual_text = manual.read_text(encoding="utf-8")
if "// bulk-discard-v1-manual" not in manual_text:
    manual_text += """
// bulk-discard-v1-manual
manualPages.find(p => p.id === 'units')?.topics.push({
  title: '批次清單保留或不保留',
  steps: [
    '批次續約及批次退租視窗底部可選「關閉並保留清單」，之後繼續未完成批次。',
    '若不要保留，點「不保留清單並返回」，確認後清除本次暫存與勾選；取消確認則繼續編輯。送出中無法關閉或清除。',
    '視窗上方「← 返回倉位」保持橫排；有未完成資料時，使用此返回鍵仍會保留清單。'
  ],
  result: '不保留僅清除本裝置此分頁的批次暫存，不會撤銷已成功送出的續約、待收款或退租。'
});
"""

page.write_text(text, encoding="utf-8")
css.write_text(css_text, encoding="utf-8")
manual.write_text(manual_text, encoding="utf-8")

print("已新增不保留清單並返回、修正返回鍵排版，並更新操作手冊。")
