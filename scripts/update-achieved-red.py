from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = {}
marker = 'storeasy-achieved-red-v1'

def replace(s, old, new, name):
    if s.count(old) != 1:
        raise RuntimeError('找不到唯一更新位置：' + name)
    return s.replace(old, new, 1)

name = 'src/GoalsOverview.tsx'
s = (root / name).read_text(encoding='utf-8')
if marker not in s:
    s = replace(
        s,
        "v>=g?'達標':'未達標'",
        'v>=g?<strong className="goal-achieved">達標</strong>:\'未達標\'',
        name
    )
    files[name] = s + '\n// ' + marker + '\n'

name = 'src/OtherGoals.tsx'
p = root / name
if p.exists():
    s = p.read_text(encoding='utf-8')
    if marker not in s:
        s = replace(
            s,
            '{r.result}',
            '{r.result===\'達標\'?<strong className="goal-achieved">達標</strong>:r.result}',
            name
        )
        files[name] = s + '\n// ' + marker + '\n'

name = 'src/Targets.tsx'
s = (root / name).read_text(encoding='utf-8')
if marker not in s:
    s = replace(
        s,
        "actual>=target?'已達標':'未達標'",
        'actual>=target?<strong className="goal-achieved">已達標</strong>:\'未達標\'',
        name
    )
    s = replace(
        s,
        "progress.completed===12&&`・${result(progress.average,annual?.performance)}`",
        "progress.completed===12&&<>・{result(progress.average,annual?.performance)}</>",
        name
    )
    s = replace(
        s,
        "progress.finalOccupancy!=null&&`・12 月 ${result(progress.finalOccupancy,annual?.occupancy)}`",
        "progress.finalOccupancy!=null&&<>・12 月 {result(progress.finalOccupancy,annual?.occupancy)}</>",
        name
    )
    files[name] = s + '\n// ' + marker + '\n'

name = 'src/annual-export.ts'
s = (root / name).read_text(encoding='utf-8')
if marker not in s:
    extra = ''' for (const sheet of book.worksheets) {
  if (sheet.name === '說明') continue;
  sheet.eachRow((row, rowNumber) => {
   if (rowNumber === 1) return;
   row.eachCell(cell => {
    if (cell.value === '達標' || cell.value === '已達標') {
     cell.font = {...cell.font, bold:true, color:{argb:'FFB91C1C'}};
    }
   });
  });
 }
'''
    s = replace(s, ' return book;', extra + ' return book;', name)
    files[name] = s + '\n// ' + marker + '\n'

name = 'src/style.css'
s = (root / name).read_text(encoding='utf-8')
if marker not in s:
    files[name] = (
        s + '\n/* ' + marker + ' */\n'
        '.goal-achieved { color: #b91c1c; font-weight: 700; }\n'
    )

for name, content in files.items():
    (root / name).write_text(content, encoding='utf-8')
    print('已更新 ' + name)

print('完成：達標文字改為紅字，無須修改 Firebase 規則。')
