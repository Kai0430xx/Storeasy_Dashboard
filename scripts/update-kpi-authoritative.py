from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
api = root / "src/api.ts"
main = root / "src/main.tsx"
rules = root / "firestore.rules"
manual = root / "src/manual-content.ts"

s = api.read_text(encoding="utf-8")

if "// kpi-authoritative-v1" not in s:
    case_start = s.index('case "importKpi":')
    case_end = s.index("    default:", case_start)
    block = s[case_start:case_end]

    old_loop = re.search(
        r"for\s*\(const\s+\w+\s+of\s+months\)\s*\{\s*const old\s*=",
        block,
    )
    writing = re.search(
        r"for\s*\(const\s+(\w+)\s+of\s+months\)"
        r"\s*\{?\s*(?:t|transaction)\.set\(",
        block,
    )

    if not old_loop or not writing:
        raise SystemExit("找不到 KPI 匯入結構，尚未修改檔案。")

    name = writing.group(1)
    block = (
        block[:old_loop.start()]
        + "// kpi-authoritative-v1: imported totals are authoritative.\n"
        + block[writing.start():]
    )
    block = re.sub(
        r"const existingMonths\s*=\s*new Map<string,\s*any>\(\);",
        "",
        block,
    )

    block, n1 = re.subn(
        r"amounts:\s*frozenAmounts\(\s*existingMonths\.get\([^)]*\),"
        r"\s*\w+\.amounts\s*\)",
        "amounts: " + name + ".amounts || {}",
        block,
    )
    block, n2 = re.subn(
        r"\|\|\s*existingMonths\.get\([^)]*\)\?\.renewByTerm\s*",
        "",
        block,
    )
    block, n3 = re.subn(
        r"amountSourceFile:[\s\S]*?:\s*files\.kpi,",
        "amountSourceFile: files.kpi,",
        block,
        count=1,
    )

    if (n1, n2, n3) != (1, 1, 1) or "existingMonths" in block:
        raise SystemExit("KPI 欄位版本不同，尚未修改檔案。")

    s = s[:case_start] + block + s[case_end:]
    s = re.sub(r",\s*frozenAmounts\b", "", s)

ui = main.read_text(encoding="utf-8")
for old in ["不覆盖即時操作紀錄", "不覆蓋即時操作紀錄"]:
    ui = ui.replace(
        old,
        "可覆蓋月統計，以本次 KPI 為準；逐筆異動紀錄保留",
    )

if "KPI 覆蓋確認" not in ui:
    anchor = "onClick={() => onSubmit(preview)}"
    if ui.count(anchor) != 1:
        raise SystemExit("找不到 KPI 確認按鈕，尚未修改檔案。")

    ui = ui.replace(
        anchor,
        """onClick={() => {
          if(kind === "kpi" && !window.confirm(
            "KPI 覆蓋確認：本次檔案所列的已結算月份將以檔案為準，覆蓋原月統計、金額及續約分項；缺少的項目不沿用舊值。原倉位現況與逐筆異動紀錄保留。確定匯入？"
          ))return;
          onSubmit(preview);
        }}""",
        1,
    )
    ui = re.sub(
        r"(<h3>\s*已結算月份：[\s\S]*?</h3>)",
        r'\1<p className="hint">'
        "此處所列月份將以本次 KPI 覆蓋既有月統計及金額，"
        "不會加總即時筆數；原倉位現況與逐筆異動紀錄保留。"
        "</p>",
        ui,
        count=1,
    )

r = rules.read_text(encoding="utf-8")

if "// kpi-authoritative-v1-rules" not in r:
    replacement = """// kpi-authoritative-v1-rules
        function keepsAmounts() {
          let incoming=request.resource.data;
          let local=request.time+duration.value(8,'h');
          let current=string(local.year())+'-'+
            (local.month()<10?'0':'')+string(local.month());
          let importing=incoming.get('source','')=='import'
            && month<current
            && incoming.get('month','')==month
            && incoming.get('updatedBy','')==request.auth.uid
            && incoming.get('updatedAt',null)==request.time
            && incoming.get('sourceFile','') is string
            && incoming.get('sourceFile','').size()>0
            && incoming.get('amountSourceFile','')==
              incoming.get('sourceFile','')
            && incoming.get('amounts',null) is map;
          return importing
            || !exists(/databases/$(database)/documents/branches/$(id)/months/$(month))
            || !('amounts' in resource.data)
            || resource.data.amounts.size()==0
            || (('amounts' in incoming)
              && incoming.amounts==resource.data.amounts);
        }"""

    r, count = re.subn(
        r"function keepsAmounts\(\)\s*\{[\s\S]*?\n?\s*\}",
        replacement,
        r,
        count=1,
    )
    if count != 1:
        raise SystemExit("找不到金額保護規則，尚未修改檔案。")

m = manual.read_text(encoding="utf-8")

if "// kpi-authoritative-v1-manual" not in m:
    m += """
// kpi-authoritative-v1-manual
manualPages.find(p => p.id === 'imports')?.topics.push({
 title:'歷史 KPI 覆蓋月統計，以檔案為準',
 steps:[
  '上傳 KPI 並分析預覽，只處理已結算月份，本月及未來月份仍排除。',
  '核對所列月份後按「確認匯入」，再確認覆蓋提示；取消確認不會寫入。無論原為即時統計或舊 KPI，本次所列月份皆以新檔案取代。',
  '總倉、已出租、新承租、續約、退租、金額及續約租期分項以本次資料為準；缺少的項目不沿用舊值，未列月份不變。',
  '原倉位現況與逐筆異動明細保留供查詢，不會加總到已匯入 KPI 的月份。「只補續約租期分項」仍只補分項，不覆蓋金額。'
 ],
 result:'重新匯入是取代統計，不是疊加筆數。此更新須同步發布 Firestore 規則，才可覆蓋已儲存金額。'
});
"""

for file, value in [
    (api, s),
    (main, ui),
    (rules, r),
    (manual, m),
]:
    file.write_text(value, encoding="utf-8")

print("已開放 KPI 覆蓋月統計及金額；請同步發布 Firestore 規則。")
