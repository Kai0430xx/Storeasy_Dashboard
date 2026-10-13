from pathlib import Path

root = Path(__file__).resolve().parents[1]
p = root / 'src/YearGoalsView.tsx'
s = p.read_text(encoding='utf-8')
marker = 'storeasy-month-result-v1'

if marker not in s:
    changes = [
        ('<th>整體月結果</th>', '<th>轉介數量</th>'),
        (
            '<td>{item.name}</td><td>{item.actual}</td><td>{status(item.result)}</td>{i===0&&<td rowSpan={list.length}>{status(r.overall)}</td>}',
            '<td>{item.name}</td><td>{item.actual}</td>{i===0&&<><td rowSpan={list.length}>{status(r.overall)}</td><td rowSpan={list.length}>{r.referrals==null?\'未填\':r.referrals>3?<strong className="referral-bonus">{r.referrals} 筆・超過 3 筆・年終加成</strong>:`${r.referrals} 筆`}</td></>}'
        ),
        (
            '「其它」採手填成果。達標顯示紅字。',
            '「其它」採手填成果。當月所有設定的目標都達成才算達標，以紅字顯示；缺少實際數值顯示資料未齊。轉介超過 3 筆以紅字標示。'
        )
    ]

    for old, new in changes:
        if s.count(old) != 1:
            raise RuntimeError(
                '找不到唯一更新位置，未修改檔案：' + old[:70]
            )
        s = s.replace(old, new, 1)

    s += '\n// ' + marker + '\n'
    p.write_text(s, encoding='utf-8')

print('已更新：每月只顯示一個達標結果，最右欄改為轉介數量。')
