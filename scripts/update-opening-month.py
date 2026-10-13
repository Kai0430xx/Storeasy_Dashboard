from pathlib import Path
import base64, gzip, json, re

root = Path(__file__).resolve().parents[1]
marker = 'storeasy-opening-month-v1'
files = {}

payload = (
    "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"
    "VmCkI1Ep+S/Jy8NNMhsAAA=="
)

data = json.loads(gzip.decompress(base64.b64decode(payload)))

for name, pairs in data['patches'].items():
    s = (root / name).read_text(encoding='utf-8')
    if marker in s:
        continue
    for old, new in pairs:
        if s.count(old) != 1:
            raise RuntimeError(
                '版本不符，未寫入檔案：' + name + '；' + old[:60]
            )
        s = s.replace(old, new, 1)
    files[name] = s + '\n// ' + marker + '\n'

name = 'src/api.ts'
s = (root / name).read_text(encoding='utf-8')
if marker not in s:
    start = s.index('case "saveBranch": {')
    end = s.index('case "saveActivity":', start)
    block = s[start:end]
    validation = r'''      const openingMonth=String(data.openingMonth||"");
      if ("openingMonth" in data && openingMonth && !/^20\d{2}-(0[1-9]|1[0-2])$/.test(openingMonth)) throw new Error("開幕月份不合法");
'''
    if block.count('      await runTransaction') != 1:
        raise RuntimeError('找不到據點更新位置')
    block = block.replace(
        '      await runTransaction',
        validation + '      await runTransaction',
        1
    )
    old = 'name: String(data.name).trim(),'
    if block.count(old) != 1:
        raise RuntimeError('找不到據點名稱欄位')
    block = block.replace(
        old,
        old + '\n            ...("openingMonth" in data ? {openingMonth:openingMonth||null} : {}),',
        1
    )
    files[name] = s[:start] + block + s[end:] + '\n// ' + marker + '\n'

name = 'src/main.tsx'
s = (root / name).read_text(encoding='utf-8')
if marker not in s:
    start = s.index('{modal.kind === "branch" && (')
    end = s.index('{modal.kind === "rentalDetails"', start)
    block = s[start:end]
    block, count = re.subn(
        r'name:\s*(f|form)\.name\s*,?',
        lambda m: 'name: ' + m[1] + '.name, openingMonth: ' + m[1] + '.openingMonth,',
        block,
        count=1
    )
    if count != 1 or block.count('<Submit busy={busy} />') != 1:
        raise RuntimeError('找不到據點設定表單')
    label = '''{global&&<label>開幕月份（年度計算起點）<input name="openingMonth" type="month" min="2000-01" max="2099-12" defaultValue={modal.openingMonth||''}/><small>未設定從 1 月計算；開幕當年度從此月份起，之後年度從 1 月起。</small></label>}
                '''
    block = block.replace(
        '<Submit busy={busy} />',
        label + '<Submit busy={busy} />',
        1
    )
    s = (s[:start] + block + s[end:]).replace('修改名稱', '據點設定')
    files[name] = s + '\n// ' + marker + '\n'

name = 'firestore.rules'
s = (root / name).read_text(encoding='utf-8')
if marker not in s:
    helper = '''function validOpening() {
    let d=request.resource.data;
    return !('openingMonth' in d) || d.openingMonth == null
     || (d.openingMonth is string && d.openingMonth.matches('20[0-9]{2}-(0[1-9]|1[0-2])'));
   }
   function balanced() {'''
    if s.count('function balanced() {') != 1 or s.count('&& balanced()') != 2:
        raise RuntimeError('找不到據點權限規則')
    s = s.replace('function balanced() {', helper, 1)
    s = s.replace('&& balanced()', '&& balanced() && validOpening()')
    pattern = r'allow update: if branchEdit\(id\)(\s*&& balanced\(\))'
    s, count = re.subn(
        pattern,
        r"allow update: if branchEdit(id) && (globalAccess() || !request.resource.data.diff(resource.data).affectedKeys().hasAny(['openingMonth']))\1",
        s,
        count=1
    )
    if count != 1:
        raise RuntimeError('找不到開幕月份權限位置')
    files[name] = s + '\n// ' + marker + '\n'

name = 'src/operating-months.js'
p = root / name
if p.exists() and p.read_text(encoding='utf-8') != data['module']:
    raise RuntimeError('請先核對現有檔案：' + name)
files[name] = data['module']

name = 'src/MonthlyGoalsTable.tsx'
p = root / name
if p.exists() and p.read_text(encoding='utf-8') != data['monthly']:
    raise RuntimeError('請先核對現有檔案：' + name)
files[name] = data['monthly']

name = 'src/GoalsOverview.tsx'
s = files.get(name, (root / name).read_text(encoding='utf-8'))
monthlyMarker = 'storeasy-monthly-goals-clean-v1'
if monthlyMarker not in s:
    start = s.index('  <h3>{month} 每月目標</h3>')
    end = s.index('  <h3>{year} 年度目標</h3>', start)
    s = (
        s[:start]
        + '  <MonthlyGoalsTable branches={branches} records={records} data={data} month={month} global={global} onEdit={onEdit}/>\n'
        + s[end:]
    )
    s = "import MonthlyGoalsTable from './MonthlyGoalsTable';\n" + s
    files[name] = s + '\n// ' + monthlyMarker + '\n'

for name, content in files.items():
    (root / name).write_text(content, encoding='utf-8')
    print('已更新 ' + name)

print('完成：請發布更新後的 Firebase 規則，再設定據點開幕月份。')
