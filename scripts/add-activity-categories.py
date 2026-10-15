from pathlib import Path
import re

if Path('src/activity-categories.js').exists():
    print('活動分類已套用。')
    raise SystemExit(0)

changes = {}

def edit(name, pattern, replacement):
    text = changes.get(name, Path(name).read_text(encoding='utf-8'))
    text, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise SystemExit(f'版本不符：{name}，未修改任何檔案。')
    changes[name] = text

name = 'src/main.tsx'
text = Path(name).read_text(encoding='utf-8')
start = text.index('{page === "activities" && (')
end = text.index('{page === "imports" && (', start)
part = text[start:end]

pattern = r'(\b(\w+)\.month\s*===\s*month\s*&&\s*!\2\.archived)'
part, count = re.subn(
    pattern,
    r'\1 && activityMatches(\2,activityCategory)',
    part
)
if count != 2:
    raise SystemExit('活動列表版本不符，未修改任何檔案。')

part = part.replace(
    '<div className="activity-grid">',
    '''<div className="toolbar">
 <label>活動分類
  <select aria-label="活動分類篩選" value={activityCategory}
   onChange={e=>setActivityCategory(e.target.value)}>
   <option value="all">全部分類</option>
   {[...activityCategories,'未分類'].map(c=>
    <option key={c} value={c}>{c}</option>
   )}
  </select>
 </label>
</div>
<div className="activity-grid">''',
    1
)

part, count = re.subn(
    r'(<h2>\s*\{(\w+)\.name\}\s*</h2>)',
    r'<span className="badge">{\2.category||"未分類"}</span>\1',
    part,
    count=1
)
if count != 1:
    raise SystemExit('找不到活動卡片，未修改任何檔案。')

part = part.replace(
    'text="本月尚無活動"',
    'text={activityCategory==="all"?"本月尚無活動":"此分類本月尚無活動"}'
)

changes[name] = (
    'import {activityCategories,activityMatches} '
    'from "./activity-categories.js";\n'
    + text[:start] + part + text[end:]
)

edit(
    name,
    r'(const work\s*=\s*useWorkTasks\(profile\);)',
    r'\1\n  const [activityCategory,setActivityCategory]=useState("all");'
)

edit(
    name,
    r'(<label>\s*活動名稱\s*<input)',
    r'''<label>活動分類
 <select name="category" aria-label="活動分類"
  required defaultValue={modal.category||''}>
  <option value="" disabled>請選擇分類</option>
  {activityCategories.map(c=>
   <option key={c} value={c}>{c}</option>
  )}
 </select>
</label>\1'''
)

edit(
    'src/api.ts',
    r'case "saveActivity":\s*\{',
    '''case "saveActivity": {
      if(data.category && !activityCategories.includes(data.category))
        throw new Error("請選擇有效的活動分類");'''
)

edit(
    'src/api.ts',
    r'(month:\s*data\.month,\s*)(name:\s*String\(data\.name\)\.trim\(\),)',
    r'\1...(data.category?{category:data.category}:{}),\2'
)

changes['src/api.ts'] = (
    'import {activityCategories} from "./activity-categories.js";\n'
    + changes['src/api.ts']
)

name = 'firestore.rules'
text = Path(name).read_text(encoding='utf-8')
start = text.index('match /activities/{activityId}')
end = text.index('match /months/{month}', start)
part = text[start:end]

part, count = re.subn(
    r'(&&\s*request\.resource\.data\.name is string)',
    r"&& (!('category' in request.resource.data) "
    r"|| request.resource.data.category in "
    r"['優惠倉','單店活動','官網活動','開幕優惠'])\1",
    part,
    count=1
)
if count != 1:
    raise SystemExit('活動權限版本不符，未修改任何檔案。')

changes[name] = text[:start] + part + text[end:]

changes['src/activity-categories.js'] = """
export const activityCategories=[
 '優惠倉','單店活動','官網活動','開幕優惠'
];
export function activityMatches(activity,category){
 return category==='all'
  ||(activity.category||'未分類')===category;
}
""".lstrip()

for name, content in changes.items():
    path = Path(name)
    backup = path.with_name(path.name + '.before-activity-categories')
    if path.exists() and not backup.exists():
        backup.write_text(
            path.read_text(encoding='utf-8'),
            encoding='utf-8'
        )
    path.write_text(content, encoding='utf-8')

print('已新增活動分類、分類篩選與卡片標示。請建置並發布 firestore.rules。')
