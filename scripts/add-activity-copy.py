from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
main = root / "src/main.tsx"
manual = root / "src/manual-content.ts"
s = main.read_text(encoding="utf-8")

if "// activity-copy-v1" not in s:
    pattern = (
        r"\{canWrite && \(\s*"
        r"(<button[\s\S]*?編輯活動\s*</button>)\s*\)\}"
    )
    matches = [
        m for m in re.finditer(pattern, s)
        if re.search(
            r'setModal\(\{\s*kind:\s*"activity"', m[1]
        )
    ]
    if len(matches) != 1:
        raise SystemExit("找不到活動編輯按鈕，尚未修改檔案。")

    match = matches[0]
    start = s.rfind(
        "{canWrite && (",
        match.start(),
        s.index("編輯活動", match.start()),
    )
    text = s[start:match.end()]
    button = re.search(
        r"\{canWrite && \(\s*(<button[\s\S]*?</button>)\s*\)\}",
        text,
    )
    if not button:
        raise SystemExit("活動按鈕結構不同，尚未修改檔案。")

    original = button[1]
    variable = re.search(r"\.\.\.(\w+)", original)
    if not variable:
        raise SystemExit("找不到活動資料，尚未修改檔案。")

    copy_button = (
        '<button type="button" className="text-button" '
        "onClick={()=>setModal(activityCopyDraft("
        + variable[1]
        + "))}>複製活動</button>"
    )
    s = (
        s[:start]
        + "{canWrite && (<>"
        + copy_button + original
        + "</>)}"
        + s[match.end():]
    )
    s = (
        "import {activityCopyDraft} from './activity-copy.js';\n"
        "// activity-copy-v1\n"
    ) + s

    s, count = re.subn(
        r'activity:\s*"活動設定"',
        'activity: modal.copy ? "複製活動" : "活動設定"',
        s,
        count=1,
    )
    if count != 1:
        raise SystemExit("找不到活動視窗標題，尚未修改檔案。")

    begin = s.index('{modal.kind === "activity" && (')
    end = s.index("</form>", begin)
    form = s[begin:end]

    handler = (
        r"onSubmit=\{\((\w+)\)\s*=>\s*"
        r"submit\(\1,\s*\((\w+)\)\s*=>\s*"
        r'call\("saveActivity",\s*\{[\s\S]*?\}\),\s*\)\s*\}'
    )
    form, count = re.subn(
        handler,
        """onSubmit={(event) => submit(event, async (form) => {
          await call("saveActivity", {
            ...form,
            id: modal.copy ? undefined : modal.id,
            branchId: modal.branchId,
          });
          if(modal.copy){
            setMonth(String(form.month));
            setActivityCategory("all");
          }
        })}""",
        form,
        count=1,
    )
    if count != 1:
        raise SystemExit("找不到活動儲存流程，尚未修改檔案。")

    hint = (
        '{modal.copy&&<p className="hint">'
        "選擇要複製到的月份，可修改名稱、分類與說明。"
        "只建立新活動，不複製使用倉位、次數或任何使用紀錄。"
        "</p>}\n"
    )
    form = re.sub(
        r"(<label>\s*活動月份)",
        lambda match: hint + match[1],
        form,
        count=1,
    )
    s = s[:begin] + form + s[end:]

module = """// activity-copy-v1: copy descriptive fields only.
export function activityCopyDraft(activity){
 const match=String(activity.month||'').match(
  /^(\\d{4})-(0[1-9]|1[0-2])$/
 );
 if(!match)throw new Error('來源活動月份不合法，請重新整理');

 const year=Number(match[1]),month=Number(match[2]);
 const next=month===12
  ?`${year+1}-01`
  :`${year}-${String(month+1).padStart(2,'0')}`;

 return {
  kind:'activity',
  copy:true,
  branchId:activity.branchId,
  month:next,
  name:activity.name||'',
  description:activity.description||'',
  category:activity.category||''
 };
}
"""

m = manual.read_text(encoding="utf-8")
if "// activity-copy-v1-manual" not in m:
    m += """
// activity-copy-v1-manual
manualPages.find(p => p.id === 'activities')?.topics.push({
 title:'複製既有活動到其他月份',
 steps:[
  '切換到原活動月份，在活動卡片按「複製活動」。具原據點編輯權限者可使用。',
  '目標月份預設為原活動的下一個月，可自行選擇；名稱、分類與說明會帶入，也可修改。舊活動未分類時請先選分類。',
  '確認儲存後，在原據點建立獨立的新活動並切換至目標月份；關閉或取消不會建立活動。'
 ],
 result:'只複製活動名稱、說明與分類，不複製活動 ID、使用倉位、使用次數、歷史承租／續約、待收款或補登活動紀錄；原活動與原紀錄保留。'
});
"""

main.write_text(s, encoding="utf-8")
(root / "src/activity-copy.js").write_text(
    module, encoding="utf-8"
)
manual.write_text(m, encoding="utf-8")
print("已新增活動複製，可選目標月份，使用紀錄不複製。")
