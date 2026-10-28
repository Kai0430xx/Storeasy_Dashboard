from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
p = root / "src/main.tsx"
manual = root / "src/manual-content.ts"
s = p.read_text(encoding="utf-8")

if "// work-account-list-v1" not in s:
    state = re.search(
        r"const work\s*=\s*useWorkTasks\(profile\);", s
    )
    selector = re.search(
        r'<select\s+aria-label="選擇據點"[\s\S]*?</select>', s
    )
    work = re.search(
        r"<WorkTasks\b[\s\S]*?/>(?=\})", s
    )

    if not state or not selector or not work:
        raise SystemExit(
            "找不到待辦與據點篩選的預期結構，尚未修改檔案。"
        )

    block = selector.group(0)
    block, n1 = re.subn(
        r"value=\{branchId\}",
        'value={page === "work" ? workBranchId : branchId}',
        block,
        count=1,
    )
    block, n2 = re.subn(
        r"onChange=\{\((\w+)\)\s*=>\s*\{setLoadAllUnits\(false\);"
        r"setBranchId\(\1.target.value\);\}\}",
        'onChange={(event)=>{if(page === "work"){'
        "setWorkBranchId(event.target.value);"
        "}else{setLoadAllUnits(false);"
        "setBranchId(event.target.value);}}}",
        block,
        count=1,
    )
    block, n3 = re.subn(
        r'(<option value="all">)\s*全部可查看據點\s*(</option>)',
        r'\1{page === "work" ? "全部可查看待辦（跨據點）"'
        r' : "全部可查看據點"}\2',
        block,
        count=1,
    )

    component = work.group(0)
    if (
        (n1, n2, n3) != (1, 1, 1)
        or "branchId={branchId}" not in component
        or "onSelectBranch={setBranchId}" not in component
    ):
        raise SystemExit("據點選單版本不同，尚未修改檔案。")

    component = component.replace(
        "branchId={branchId}", "branchId={workBranchId}"
    ).replace(
        "onSelectBranch={setBranchId}",
        "onSelectBranch={setWorkBranchId}",
    )

    s = s.replace(work.group(0), component, 1)
    s = s.replace(selector.group(0), block, 1)
    s = s.replace(
        state.group(0),
        state.group(0) + """
  // work-account-list-v1
  const [workBranchId, setWorkBranchId] = useState("all");
  useEffect(() => {
    if (page === "work") setWorkBranchId("all");
  }, [page, profile?.username]);
""",
        1,
    )

m = manual.read_text(encoding="utf-8")
if "// work-account-list-v1-manual" not in m:
    m += """
// work-account-list-v1-manual
manualPages.find(p => p.id === 'work')?.topics.push({
  title: '依帳號查看跨據點待辦',
  steps: [
    '進入待辦事項時，預設「全部可查看待辦（跨據點）」，彙整此帳號原本有權查看的事項，不必逐店切換；直接指派給帳號的跨店事項也會列入。',
    '每筆保留原據點或共同協作的參與據點。需要單店查看時，再切換待辦頁的據點選單。',
    '待辦篩選與倉位、候補等頁面的據點選擇互不影響；離開再進入待辦會恢復跨據點清單。搜尋、分類、未完成及已完成篩選仍可使用。'
  ],
  result: '指派仍綁定帳號；本次只調整清單篩選，不擴大讀寫權限，不改變通知對象。跨據點清單包含所有可查看事項，不僅是直接指派給自己的事項。'
});
"""

p.write_text(s, encoding="utf-8")
manual.write_text(m, encoding="utf-8")
print("已改為帳號跨據點待辦清單，並更新操作手冊。")
