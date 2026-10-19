from pathlib import Path
import re

r = Path(__file__).resolve().parents[1]
changes = {}

helper = r'''
  // unpaid-overdue-v1: payment overdue is independent of the new lease end.
  const unpaid = pending.some(row => {
    if (row.status !== 'pending' || row.branchId !== unit.branchId || row.code !== unit.code) return false;
    let start = row.leaseStart;
    if (!start) {
      try { start = parseLease(row.leasePeriod).leaseStart; }
      catch { return false; }
    }
    return validDate(start) && start <= date;
  });
  if (unpaid) return { key: 'overdue', label: '已逾期（待收款）', color: 'red' };
'''

p = r / 'src/lease.js'
s = p.read_text()
if '// unpaid-overdue-v1' not in s:
    old = 'export function leaseStatus(unit, date = taipeiDate()) {'
    assert old in s, '找不到租期狀態函式，未寫入'
    s = s.replace(
        old,
        'export function leaseStatus(unit, date = taipeiDate(), pending = []) {'
    )
    anchor = '  if (!unit.leaseEnd)'
    assert anchor in s
    s = s.replace(anchor, helper + anchor)
changes[p] = s

p = r / 'src/main.tsx'
s = p.read_text()
s, n = re.subn(
    r'leaseStatus\((\w+), currentDate\)',
    r'leaseStatus(\1, currentDate, pendingRenewals)',
    s
)
assert n == 3 or 'currentDate, pendingRenewals)' in s, '找不到倉位狀態，未寫入'
changes[p] = s

p = r / 'src/pending-renewals.ts'
s = p.read_text()
if 'String(data.date||taipeiDate())' not in s:
    s = s.replace(
        'data.date||taipeiDate()',
        'String(data.date||taipeiDate())'
    )
s = s.replace(
    "month=String(data.month||'')",
    "month=String(date).slice(0,7)"
)
assert 'month=String(date).slice(0,7)' in s, '找不到收款月份，未寫入'
changes[p] = s

p = r / 'src/PendingRenewals.tsx'
s = p.read_text()
if '未付款租期已開始時' not in s:
    anchor = '此處會保留所有未確認收款的租期，即使目前倉位已換租期或退租。'
    assert anchor in s
    s = s.replace(
        anchor,
        anchor + '未付款租期已開始時，已出租倉位也會列入「已逾期」，不以新租期結束日延後提醒。'
    )

a = s.index('function Payment(')
b = s.index('export function usePendingRenewals', a)
part = s[a:b]
if 'const [paymentDate,setPaymentDate]' not in part:
    anchor = ' const [open,setOpen]=useState(false);'
    assert anchor in part
    part = part.replace(
        anchor,
        anchor + '\n const [paymentDate,setPaymentDate]=useState(taipeiDate());'
    )
    part = part.replace(
        'name="date" required max={taipeiDate()} defaultValue={taipeiDate()}',
        'name="date" required max={taipeiDate()} value={paymentDate} onChange={e=>setPaymentDate(e.target.value)}'
    )
    part = part.replace(
        'name="month" required defaultValue={taipeiDate().slice(0,7)}',
        'name="month" required readOnly value={paymentDate.slice(0,7)}'
    )
    part = part.replace(
        '已有歷史 KPI 的月份只保留收款紀錄',
        '統計月份依實際收款日期自動帶入，不依登記續約或租期月份。已有歷史 KPI 的月份只保留收款紀錄'
    )
assert 'value={paymentDate}' in part
assert 'readOnly value={paymentDate.slice(0,7)}' in part
s = s[:a] + part + s[b:]
changes[p] = s

p = r / 'firestore.rules'
s = p.read_text()
if '/* payment-month-v1 */' not in s:
    a = s.index('    function paymentCreate() {')
    b = s.index('    function paymentVoid()', a)
    part = s[a:b]
    anchor = "e.date.matches('[0-9]{4}-[0-9]{2}-[0-9]{2}')"
    assert anchor in part
    part = part.replace(
        anchor,
        anchor + " && e.date.matches(e.month+'-[0-9]{2}') /* payment-month-v1 */"
    )
    s = s[:a] + part + s[b:]
changes[p] = s

p = r / 'src/WaitingList.tsx'
s = p.read_text()
m = re.search(
    r'<input\s+className="waiting-read-check"[\s\S]*?/>',
    s
)
assert m, '找不到候補勾選框，請先套用候補批次已讀更新'
checkbox = m.group()
s = s[:m.start()] + s[m.end():]
anchor = '<td data-label="登記日期">'
assert anchor in s
s = s.replace(anchor, anchor + checkbox)
changes[p] = s

p = r / 'src/manual-content.ts'
s = p.read_text()
if '// unpaid-overdue-v1-manual' not in s:
    s += r'''
// unpaid-overdue-v1-manual
manualPages.find(p=>p.id==='units')?.topics.push({title:'未付款續約同時列入已逾期',steps:['登記續約選「未付款」後，待收款紀錄保留。只要該筆未付款租期已開始，已出租倉位同時列入「已逾期」，顯示「已逾期（待收款）」，不因新租期結束日尚未到而隱藏。','例：2026/07/25－2026/10/24 尚未收款，10/19 即顯示收款逾期；尚未開始的未付款租期則不會提早判為收款逾期。','確認收款後清除該筆待收款提醒；若仍有其它已開始的未付款租期，繼續顯示收款逾期。全部收款後仍依倉位租期判斷，租期本身已過期仍列已逾期。'],result:'只調整狀態顯示與已逾期篩選，不更改租期、待收款資料、活動或續約筆數。續約月份依收款確認，租期分項依完整租期分類。'});

// payment-month-v1-manual
manualPages.find(p=>p.id==='units')?.topics.push({title:'續約按實際收款月份計入，租期分類分開判斷',steps:['9 月登記續約且選未付款，不計入 9 月續約。10 月按確認收款，收款日期填 10 月的實際日期，統計月份自動帶入 10 月，計入 10 月續約 1 筆。','收款日期才決定續約歸屬月份；不是登記續約日期，也不是租期起訖月份。即使該期租期已結束仍可確認收款，不改動目前倉位租期。','月繳、季繳、半年繳及年繳等分項依該筆續約保存的完整租期分類；歸屬月份仍為收款月份。'],result:'確認收款不重複加計同一筆。已匯入歷史 KPI 的月份保留收款明細，不另增加彙總，避免重複計算。'});
'''
if '// waiting-date-checkbox-v1-manual' not in s:
    s += r'''
// waiting-date-checkbox-v1-manual
manualPages.find(p=>p.id==='waiting')?.topics.push({title:'候補勾選框位置',steps:['每筆候補勾選框位於登記日期前面；勾選與全部已讀功能不變。'],result:'只調整位置，不更改候補或已讀資料。'});
'''
changes[p] = s

for p, s in changes.items():
    p.write_text(s, encoding='utf-8')

print('已更新收款月份、未付款逾期與候補勾選位置。請發布最新 firestore.rules。')
