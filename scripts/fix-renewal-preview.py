from pathlib import Path

root = Path(__file__).resolve().parents[1]
css_path = root / 'src/renewal-presets.css'
manual_path = root / 'src/manual-content.ts'

css = css_path.read_text(encoding='utf-8')
if '/* renewal-preview-no-inner-scroll-v3 */' not in css:
    css += '''
/* renewal-preview-no-inner-scroll-v3 */
.modal fieldset.renewal-presets,
.renewal-presets{
  max-height:none;
  height:auto;
  overflow:visible;
}
.modal.bulk-unit-modal .bulk-unit-card>fieldset{
  max-height:none;
  height:auto;
  overflow:visible;
}
'''

manual = manual_path.read_text(encoding='utf-8')
if '// renewal-preview-no-inner-scroll-v3-manual' not in manual:
    manual += '''
// renewal-preview-no-inner-scroll-v3-manual
manualPages.find(p=>p.id==='units')?.topics.push({title:'續約預覽直接顯示',steps:['選擇續約開始日與1至12個月後，租期預覽及「確定套用」直接顯示在月數選單下方。','快速選擇租期區塊自動展開，不再有區塊內的獨立捲軸；單筆及批次續約皆適用。','整個續約視窗仍可正常捲動，以查看付款狀態、活動及最後的確認儲存。'],result:'只調整版面，不改租期計算、資料、付款狀態或送出流程。'});
'''

for path, content in [
    (css_path, css),
    (manual_path, manual),
]:
    if path.read_text(encoding='utf-8') != content:
        path.write_text(content, encoding='utf-8')

print('續約預覽已改為直接顯示，取消區塊內捲軸。')
print('本次不需部署 Firebase。')
