from pathlib import Path
import base64, gzip, json

root = Path(__file__).resolve().parents[1]
marker = "storeasy-other-monthly-v1"
payload = (
    "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"
    "BbwvNWc8MAAA"
)
data = json.loads(gzip.decompress(base64.b64decode(payload)))
files = {}

for name, pairs in data["patches"].items():
    s = (root / name).read_text(encoding="utf-8")
    if marker in s:
        continue
    for old, new in pairs:
        if s.count(old) != 1:
            raise RuntimeError(
                "版本不符，尚未寫入檔案：" + name + "；" + old[:60]
            )
        s = s.replace(old, new, 1)
    files[name] = s + "\n// " + marker + "\n"

for name, content in data["new"].items():
    p = root / name
    if p.exists() and p.read_text(encoding="utf-8") != content:
        raise RuntimeError("請先核對現有檔案：" + name)
    files[name] = content

s = (root / "src/style.css").read_text(encoding="utf-8")
if marker not in s:
    files["src/style.css"] = s + data["css"] + "\n/* " + marker + " */\n"

for name, content in files.items():
    (root / name).write_text(content, encoding="utf-8")
    print("已更新 " + name)

print("完成：請將 GitHub firestore.rules 全文複製到 Firebase 規則頁發布。")
