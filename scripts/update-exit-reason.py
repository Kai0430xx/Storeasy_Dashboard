from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
files = {}


def read(name):
    return (root / name).read_text(encoding="utf-8")


def replace(text, old, new):
    if old not in text:
        raise RuntimeError("找不到替換位置：" + old[:100])
    return text.replace(old, new, 1)


if 'name="exitReason"' in read("src/main.tsx"):
    print("退租原因已更新。")
    raise SystemExit(0)

s = read("src/api.ts")
s = replace(
    s,
    "        const lease = parseLease(",
    '''        const exitReason = type === "exit" && typeof data.exitReason === "string"
          ? data.exitReason.trim() : "";
        if (type === "exit" && (!exitReason || exitReason.length > 500))
          throw new Error("退租原因請填寫 1～500 字，不能只有空白");
        const lease = parseLease(''',
)
s = replace(
    s,
    "          priceSnapshot: priceSnapshot(unit, date),",
    "          exitReason,\n          priceSnapshot: priceSnapshot(unit, date),",
)
files["src/api.ts"] = s

s = read("src/main.tsx")
s = replace(
    s,
    'activityIds: form.getAll("activity"),',
    'activityIds: form.getAll("activity"),\n                      exitReason: form.get("exitReason"),',
)
s = replace(
    s,
    '{modal.type !== "exit" && (',
    '''{modal.type === "exit" && (
                  <label>
                    退租原因
                    <textarea
                      name="exitReason"
                      required
                      maxLength={500}
                      rows={3}
                      placeholder="請填寫退租原因，最多 500 字"
                    />
                  </label>
                )}
                {modal.type !== "exit" && (''',
)

start = s.index("<h2>異動紀錄")
end = s.index('{page === "activities"', start)
block = replace(
    s[start:end],
    "<th>使用活動</th>",
    "<th>使用活動</th><th>退租原因</th>",
)
block, count = re.subn(
    r"(\{event\.activities.*?\}\s*</td>)",
    lambda match: match.group(1) +
    '\n                                <td className="exit-reason">{event.type === "exit" ? event.exitReason || "未記錄" : "—"}</td>',
    block,
    count=1,
    flags=re.S,
)
if count != 1:
    raise RuntimeError("找不到異動紀錄顯示位置")

files["src/main.tsx"] = s[:start] + block + s[end:]

s = read("src/RentalDetails.tsx")
s = replace(
    s,
    "<th>備註</th>",
    '{type === "exit" && <th>退租原因</th>}<th>備註</th>',
)
s = replace(
    s,
    '<td>{row.details.note || "—"}</td>',
    '{type === "exit" && <td className="exit-reason">{row.exitReason || "未記錄"}</td>}<td>{row.details.note || "—"}</td>',
)
files["src/RentalDetails.tsx"] = s

files["src/style.css"] = read("src/style.css") + """
.exit-reason {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  min-width: 160px;
  max-width: 320px;
}
"""

for name, content in files.items():
    (root / name).write_text(content, encoding="utf-8")
    print("已更新 " + name)
