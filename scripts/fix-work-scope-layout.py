from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
source = root / "src/my-work-scope.tsx"
manual = root / "src/manual-content.ts"

s = source.read_text(encoding="utf-8")
pattern = r"export function WorkScopePicker\([\s\S]*$"

if len(re.findall(pattern, s)) != 1:
    raise SystemExit("找不到待辦範圍選單，尚未修改檔案。")

s = re.sub(
    pattern,
    """export function WorkScopePicker({scope,onChange}:{
 scope:string;
 onChange:(value:string)=>void;
}){
 return <select className="work-scope-select"
  aria-label="待辦範圍" title="待辦範圍"
  value={scope} onChange={e=>onChange(e.target.value)}>
  <option value="mine">我的據點＋指派給我</option>
  <option value="all">全部可查看待辦</option>
 </select>;
}
""",
    s,
    count=1,
)

if "import './work-scope-layout.css';" not in s:
    s = "import './work-scope-layout.css';\n" + s

styles = """/* work-scope-layout-v1 */
.work-area > .work-filters {
  align-items: center;
  gap: 10px;
}
.work-area > .work-filters > .work-scope-select {
  flex: 0 1 230px;
  width: 230px;
  max-width: 100%;
  min-width: 0;
  height: 42px;
  box-sizing: border-box;
  margin: 0;
  padding: 8px 12px;
}
.work-area > .work-filters > .clearable-search input {
  height: 42px;
  box-sizing: border-box;
}
.work-area > .work-filters > label {
  margin: 0;
  white-space: nowrap;
}
@media (max-width: 760px) {
  .work-area > .work-filters > .work-scope-select,
  .work-area > .work-filters > .clearable-search {
    flex: 1 1 100%;
    width: 100%;
    max-width: none;
    min-width: 0;
  }
}
"""

m = manual.read_text(encoding="utf-8")
if "// work-scope-layout-v1-manual" not in m:
    m += """
// work-scope-layout-v1-manual
manualPages.find(p => p.id === 'work')?.topics.push({
 title:'待辦範圍選單的位置',
 steps:[
  '電腦的待辦範圍選單與搜尋框同高對齊，選單上方不另占一行標籤；可選「我的據點＋指派給我」或「全部可查看待辦」。',
  '手機將範圍選單、標題搜尋及指派對象搜尋各自排成一整行，逾期與未讀勾選接在下方。'
 ],
 result:'只調整篩選列外觀，原本的預設範圍、據點及帳號權限不變。'
});
"""

source.write_text(s, encoding="utf-8")
(root / "src/work-scope-layout.css").write_text(
    styles, encoding="utf-8"
)
manual.write_text(m, encoding="utf-8")
print("已整理待辦範圍與搜尋列排版。")
