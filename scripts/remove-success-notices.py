from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
updates = {}

# 僅移除操作成功提示，保留錯誤、進度、篩選及批次結果。
notice_files = [
    'src/main.tsx',
    'src/CalendarPage.tsx',
    'src/WorkTasks.tsx',
    'src/Targets.tsx',
    'src/BranchCheers.tsx',
    'src/MonthlyEntry.tsx',
    'src/NotificationCenter.tsx',
    'src/OwnNotificationBranches.tsx',
]

pattern = re.compile(
    r'\{notice\s*&&\s*(?:\(\s*)?'
    r'<(p|div|small)\b[^>]*>[\s\S]*?</\1>\s*(?:\))?\}'
)

for name in notice_files:
    path = root / name
    if not path.exists():
        raise SystemExit(f'找不到 {name}，尚未修改檔案。')

    original = path.read_text(encoding='utf-8')
    updated, count = pattern.subn('', original)

    if count > 1 or (
        count == 0 and re.search(r'\{notice\s*&&', original)
    ):
        raise SystemExit(
            f'{name} 的格式不同，尚未修改檔案。請提供錯誤訊息。'
        )

    updates[path] = updated

name = 'src/WaitingList.tsx'
path = root / name
original = path.read_text(encoding='utf-8')

updated, count = re.subn(
    r'\{savedNotice\s*&&\s*!edit\s*&&\s*'
    r'<div\b[^>]*>[\s\S]*?</div>\}',
    '',
    original
)

if count > 1 or (
    count == 0 and '{savedNotice&&' in original
):
    raise SystemExit(f'{name} 的格式不同，尚未修改檔案。')

updates[path] = updated

# 活動補登的訊息同時包含成功與錯誤，只清除成功文字。
path = root / 'src/ActivitySupplement.tsx'
original = path.read_text(encoding='utf-8')

updates[path] = original.replace(
    "setMessage('當月活動已補登')",
    "setMessage('')"
)

# 保留處理進度及失敗明細，只移除全部成功與匯出成功文字。
path = root / 'src/GoalsOverview.tsx'
original = path.read_text(encoding='utf-8')

old = "setMessage(`成功 ${completed} 間${failed.length?`；失敗 ${failed.length} 間：${failed.join('；')}`:''}`)"
new = "setMessage(failed.length?`成功 ${completed} 間；失敗 ${failed.length} 間：${failed.join('；')}`:'')"

if old not in original and new not in original:
    raise SystemExit(
        'GoalsOverview.tsx 的格式不同，尚未修改檔案。'
    )

updated = original.replace(old, new).replace(
    'setMessage(`${year} 年度 Excel 已匯出`)',
    'setMessage("")'
)

updates[path] = updated

# 同步更新操作手冊。
path = root / 'src/manual-content.ts'
original = path.read_text(encoding='utf-8')
marker = '// quiet-success-notices-v1-manual'

manual = '''
// quiet-success-notices-v1-manual
manualPages.find(p=>p.id==='dashboard')?.topics.push({
 title:'操作成功後不再顯示提示橫幅',
 steps:[
  '各頁面新增、儲存、修改、刪除、匯入或完成設定後，不再顯示需要手動關閉的成功提示。可直接在更新後的清單或資料確認結果。',
  '操作失敗、權限不足及填寫錯誤仍會顯示，請依訊息修正。處理中的進度、待確認畫面與批次成功／失敗／待處理筆數仍保留。',
  '此調整不影響鈴鐺未讀、日曆修改申請及手機背景推播；候補篩選條件提示與還原篩選按鈕也保留。'
 ],
 result:'不會自動關閉錯誤訊息，也不改變資料儲存、刪除或通知權限。'
});
'''

updates[path] = (
    original if marker in original else original + manual
)

# 全部檢查完成後才寫入，可重複執行。
changed = 0

for path, updated in updates.items():
    if path.read_text(encoding='utf-8') != updated:
        path.write_text(updated, encoding='utf-8')
        changed += 1

print(
    f'成功提示更新完成，共修改 {changed} 個檔案。'
    '錯誤與批次結果保留。'
)
print('本次不需重新部署 Firebase。')
