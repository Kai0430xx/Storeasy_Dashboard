from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
source = root / "src/raw-inventory.js"
manual = root / "src/manual-content.ts"

text = source.read_text(encoding="utf-8")
pattern = r"function cleanDimensions\([^)]*\)\s*\{[\s\S]*?\n\}"

if len(re.findall(pattern, text)) != 1:
    raise SystemExit("找不到尺寸處理函式，尚未修改任何檔案。")

text = re.sub(
    pattern,
    """function cleanDimensions(value,cell,fixes){
 // dimensions-as-text-v1
 return String(value ?? '');
}""",
    text,
    count=1,
)

# 尺寸空白也不阻擋；倉號等其他檢查繼續保留。
text = re.sub(r"\|\|\s*!norm\(r\[2\]\)", "", text)

manual_text = manual.read_text(encoding="utf-8")
manual_text = manual_text.replace(
    "尺寸後誤接的純數字會移除",
    "尺寸依 Excel 文字保留，不檢查算式，也不移除尾端文字或數字",
)

if "// dimensions-as-text-v1-manual" not in manual_text:
    manual_text += """
// dimensions-as-text-v1-manual
manualPages.find(p => p.id === 'imports')?.topics.push({
  title: '特殊尺寸直接依 Excel 匯入',
  steps: [
    '尺寸當作文字讀取，括號、加減號、不完整乘式、換行及文字說明均可保留；尺寸留空也不阻擋。原始下載檔與有標題表格皆適用。',
    '材積、單價與月租仍讀取各自欄位，不從尺寸計算；租期仍依租期欄判斷。匯入預覽確認後才會儲存。'
  ],
  result: '只放寬尺寸格式，倉號、數值、租期及重複倉位檢查繼續保留。尺寸仍沿用系統原有的最多 100 字儲存限制。'
});
"""

source.write_text(text, encoding="utf-8")
manual.write_text(manual_text, encoding="utf-8")

print("已改為直接讀取 Excel 尺寸文字，並更新操作手冊。")
