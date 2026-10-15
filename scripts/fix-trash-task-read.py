from pathlib import Path

path = Path('src/WorkTasks.tsx')
text = path.read_text(encoding='utf-8')
marker = '// storeasy-trash-read-v1'

if marker in text:
    print('垃圾桶事項已讀修正已套用。')
    raise SystemExit(0)

old = '(!task.deleted)'
if text.count(old) != 2:
    raise SystemExit('已讀程式版本不符，未修改任何檔案。')

text = text.replace(
    old,
    '(!task.purging&&(!task.deleted||global))'
)

old = '[selected,thread,otherLatest,Boolean(dialog),inactive,quotaBlocked]'
if text.count(old) != 1:
    raise SystemExit('找不到已讀更新設定，未修改任何檔案。')

text = text.replace(
    old,
    '[selected,thread,otherLatest,Boolean(dialog),Boolean(item),'
    'inactive,quotaBlocked,global,task?.purging]'
)

old = '[task,thread,dialog,inactive,reads,quotaBlocked]'
if text.count(old) != 1:
    raise SystemExit('找不到視窗已讀設定，未修改任何檔案。')

text = text.replace(
    old,
    '[task,thread,dialog,inactive,reads,quotaBlocked,global]'
)

text = text.replace(
    "if(task&&!dialog&&!quotaBlocked&&item&&",
    "if(document.visibilityState==='visible'"
    "&&task&&!dialog&&!quotaBlocked&&item&&"
)

backup = path.with_name(path.name + '.before-trash-read-fix')
if not backup.exists():
    backup.write_text(
        path.read_text(encoding='utf-8'),
        encoding='utf-8'
    )

path.write_text(text + '\n' + marker + '\n', encoding='utf-8')
print('已修正：直接點開垃圾桶事項也會標記已讀。')
