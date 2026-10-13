from pathlib import Path

root = Path(__file__).resolve().parents[1]
marker = 'storeasy-referral-red-v1'
files = {}

changes = {
    'src/MonthlyGoalsTable.tsx': [
        (
            'format:(n:any)=>any=(n)=>n)',
            'format:(n:any)=>any=(n)=>n,red=false)'
        ),
        (
            'actual!=null&&<span>',
            'actual!=null&&<span className={red?"goal-achieved":undefined}>'
        ),
        (
            'values(r.referralTarget,r.referrals)}{r.referrals>3&&<strong className="referral-bonus">超過 3 筆・年終加成</strong>}',
            'values(r.referralTarget,r.referrals,(n)=>n,r.referrals>=3)}'
        )
    ],
    'src/YearGoalsView.tsx': [
        ('r.referrals>3?', 'r.referrals>=3?'),
        (
            '<strong className="referral-bonus">{r.referrals} 筆・超過 3 筆・年終加成</strong>',
            '<strong className="goal-achieved">{r.referrals} 筆</strong>'
        )
    ]
}

for name, pairs in changes.items():
    s = (root / name).read_text(encoding='utf-8')
    if marker in s:
        continue
    for old, new in pairs:
        if s.count(old) != 1:
            raise RuntimeError(
                '找不到唯一更新位置，未寫入檔案：' + name
            )
        s = s.replace(old, new, 1)
    files[name] = s + '\n// ' + marker + '\n'

for name, content in files.items():
    (root / name).write_text(content, encoding='utf-8')
    print('已更新 ' + name)

print('完成：實際轉介 3 筆以上只顯示紅字數量。')
