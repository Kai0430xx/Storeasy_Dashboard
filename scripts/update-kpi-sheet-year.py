from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
p = root / 'src/imports.js'
s = p.read_text(encoding='utf-8')

pattern = r'const year\s*=\s*String\(rows\[0\]\?\.\[1\]\s*\|\|\s*name\)\s*\.match\(/20\\d\{2\}/\)\?\.\[0\];'

new = r'''const year = String(rows[0]?.[1] ?? "").match(/20\d{2}/)?.[0]
      || String(name).match(/20\d{2}/)?.[0];'''

if new not in s:
    s, count = re.subn(pattern, lambda _: new, s)
    if count != 1:
        raise RuntimeError('找不到唯一年份辨識位置，未修改檔案')

p.write_text(s, encoding='utf-8')
print('已修正：表頭找不到年份時，改從頁簽名稱辨識。')
