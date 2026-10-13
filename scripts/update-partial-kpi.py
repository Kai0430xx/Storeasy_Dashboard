from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
files = {}

p = root / "src/api.ts"
s = p.read_text(encoding="utf-8")

if '總倉或出租數不完整' in s:
    pattern = (
        r'if\s*\(\s*(m|month)\.total === null\s*\|\|'
        r'\s*\1\.rented === null\s*\|\|'
        r'\s*\1\.rented > \1\.total\s*\)'
    )

    def replacement(match):
        name = match[1]
        return (
            f'if ({name}.total !== null'
            f' && {name}.rented !== null'
            f' && {name}.rented > {name}.total)'
        )

    s, count = re.subn(pattern, replacement, s, count=1)
    if count != 1:
        raise RuntimeError("找不到 KPI 欄位檢查位置")

    s = s.replace(
        '總倉或出租數不完整',
        '已出租數不可大於總倉數',
    )

files["src/api.ts"] = s

p = root / "firestore.rules"
s = p.read_text(encoding="utf-8")

if '|| request.resource.data.total == null' not in s:
    old = "|| !('rented' in request.resource.data)"
    if s.count(old) != 1:
        raise RuntimeError("找不到 KPI 月份規則位置")

    s = s.replace(
        old,
        old
        + '\n            || request.resource.data.total == null'
        + '\n            || request.resource.data.rented == null',
        1,
    )

files["firestore.rules"] = s

for name, content in files.items():
    (root / name).write_text(content, encoding="utf-8")
    print("已更新 " + name)
