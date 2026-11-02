from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
updates = {}

for name in ["Targets.tsx", "MonthlyEntry.tsx"]:
    p = root / "src" / name
    text = p.read_text(encoding="utf-8")

    text = re.sub(
        r'\{(?:ref\?\.count|entries\.length)>3&&'
        r'<(?:span|strong) className="referral-bonus">'
        r'超過 3 筆・年終加成</(?:span|strong)>\}',
        "",
        text,
    )
    text = text.replace(
        "{entries.length>3?'・超過 3 間，年終加成':''}",
        "",
    )

    if "年終加成" in text:
        raise SystemExit(name + " 格式不同，尚未修改檔案。")

    updates[p] = text

p = root / "src/annual-export.ts"
text = p.read_text(encoding="utf-8")
text = text.replace(
    "bonus:ref?.count>3?'超過 3 筆・年終加成':''",
    "bonus:''",
)
text = re.sub(
    r"\{header:'轉介加成提示',key:'bonus',width:26\},?",
    "",
    text,
)
text = text.replace(
    "['轉介提示','當月超過 3 筆以紅字標示年終加成，未自行計算獎金。'],",
    "",
)

if "年終加成" in text:
    raise SystemExit("匯出格式不同，尚未修改檔案。")

updates[p] = text

p = root / "src/manual-content.ts"
text = p.read_text(encoding="utf-8")

if "// remove-referral-bonus-text-v1" not in text:
    text += """
// remove-referral-bonus-text-v1
manualPages.find(p => p.id === 'targets')?.topics.push({
 title:'轉介數量與達標顯示',
 steps:['轉介欄保留實際筆數、設定目標與達標結果，不另顯示加成文字提示。轉介編輯視窗及之後匯出的年度 Excel 也不再顯示該提示。'],
 result:'只移除提示文字與 Excel 提示欄，不更動轉介紀錄、數量、目標或達標計算。已下載的舊 Excel 不會自動更新。'
});
"""

updates[p] = text

for p, text in updates.items():
    p.write_text(text, encoding="utf-8")

print("已移除提示文字，保留轉介數量與達標結果。")
