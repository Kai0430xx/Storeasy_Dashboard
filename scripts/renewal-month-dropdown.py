from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
updates = {}

path = root / 'src/RenewalLeaseField.tsx'
text = path.read_text(encoding='utf-8')

select = '''<label>續約月數<select aria-label={`${ariaLabel} 月數`} value={months??''} onChange={e=>setMonths(e.target.value?Number(e.target.value):null)}><option value="">請選擇月數</option>{Array.from({length:12},(_,i)=>i+1).map(n=><option key={n} value={n}>{n}個月</option>)}</select></label>'''

if select not in text:
    text, count = re.subn(
        r'<div className="renewal-preset-buttons">[^\n]*</div>',
        lambda _: select,
        text,
    )
    if count != 1:
        raise SystemExit(
            '找不到原租期按鈕，尚未修改檔案。請提供錯誤訊息。'
        )

text = text.replace(
    '非1、3、6、12個月，可直接手動輸入完整起訖日期。',
    '特殊租期或非整月，可直接手動輸入完整起訖日期。'
)
updates[path] = text

path = root / 'src/renewal-presets.js'
text = path.read_text(encoding='utf-8')

old = '![1,3,6,12].includes(months)'
new = '!Number.isInteger(months)||months<1||months>12'

if old not in text and new not in text:
    raise SystemExit(
        '租期計算程式版本不同，尚未修改檔案。'
    )

updates[path] = text.replace(old, new)

path = root / 'src/renewal-presets.css'
text = path.read_text(encoding='utf-8')

if '/* renewal-month-dropdown-v2 */' not in text:
    text += '''
/* renewal-month-dropdown-v2 */
.renewal-presets select{width:100%;min-width:0}
'''

updates[path] = text

path = root / 'src/manual-content.ts'
text = path.read_text(encoding='utf-8')

text = text.replace(
    '續約快速選擇月租、季租、半年租及年租',
    '續約下拉選擇1至12個月'
).replace(
    '登記續約及批次續約的新租期上方可選月租1個月、季租3個月、半年租6個月、年租12個月。',
    '登記續約及批次續約的新租期上方，使用「續約月數」下拉選單選擇1至12個月。'
).replace(
    '不是1、3、6、12個月時，直接手動輸入下方完整租期即可。',
    '特殊租期或非整月時，直接手動輸入下方完整租期即可。'
).replace(
    '按預設選項只會改預覽',
    '選擇月數只會改預覽'
)

if '// renewal-month-dropdown-v2-manual' not in text:
    text += '''
// renewal-month-dropdown-v2-manual
manualPages.find(p=>p.id==='units')?.topics.push({title:'續約月數下拉選單',steps:['單筆及批次續約改用下拉選單，提供1個月至12個月；不再顯示月租、季租、半年租、年租四個按鈕。','選擇開始日與月數後查看預覽，再按「確定套用」帶入租期；特殊租期仍可在下方手動輸入。','月底規則不變：目標月份沒有同日，先取月底再往前一天；1/31月租到2/27，閏年到2/28。'],result:'套用租期不會直接儲存續約，也不改收款日期、付款狀態或活動。'});
'''

updates[path] = text

changed = 0
for path, text in updates.items():
    if path.read_text(encoding='utf-8') != text:
        path.write_text(text, encoding='utf-8')
        changed += 1

print(f'續約已改為1至12個月下拉選單，共修改 {changed} 個檔案。')
print('本次不需部署 Firebase。')
