from pathlib import Path
import re

service = Path('src/pending-renewals.ts')

if 'export async function deletePendingRenewal' in service.read_text(encoding='utf-8'):
    print('待收款刪除功能已套用。')
    raise SystemExit(0)

changes = {}

def edit(name, pattern, replacement):
    text = changes.get(name, Path(name).read_text(encoding='utf-8'))
    text, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise SystemExit(f'版本不符：{name}，未修改任何檔案。')
    changes[name] = text

edit(
    'src/api.ts',
    r'(import\s*\{)([^}]*)(\}\s*from\s*[\'"]\./pending-renewals[\'"])',
    r'\1deletePendingRenewal,\2\3'
)

edit(
    'src/api.ts',
    r'case "confirmRenewalPayment":',
    'case "deletePendingRenewal": return deletePendingRenewal(data);\n'
    '    case "confirmRenewalPayment":'
)

edit(
    'src/PendingRenewals.tsx',
    r'(>\s*確認收款\s*</button>)',
    r'''\1
  <button
   type="button"
   className="text-button danger"
   disabled={busy}
   style={{marginLeft:12}}
   onClick={()=>{
    if(!window.confirm(`確定刪除 ${row.code} 的這筆待收款？\n只移除待收款紀錄，保留目前租期，不變更續約筆數。`))return;
    onSave(
     ()=>call('deletePendingRenewal',{
      branchId:row.branchId,
      pendingId:row.id
     }),
     '待收款紀錄已刪除'
    );
   }}
  >刪除</button>'''
)

name = 'firestore.rules'
text = Path(name).read_text(encoding='utf-8')
start = text.index('match /pendingRenewals/{pendingId}')
end = text.index('match /events/{eventId}', start)

section, count = re.subn(
    r'allow delete:\s*if false;',
    "allow delete: if branchEdit(id) && unlocked(id) "
    "&& resource.data.status=='pending';",
    text[start:end],
    count=1
)

if count != 1:
    raise SystemExit('找不到待收款權限設定，未修改任何檔案。')

changes[name] = text[:start] + section + text[end:]

changes[str(service)] = service.read_text(encoding='utf-8') + r'''

export async function deletePendingRenewal(data:any){
 const uid=auth.currentUser?.uid;
 if(!uid)throw new Error('請先登入');

 const b=doc(db,'branches',data.branchId);
 const p=doc(b,'pendingRenewals',data.pendingId);

 await runTransaction(db,async tx=>{
  const [bs,ps]=await Promise.all([tx.get(b),tx.get(p)]);

  if(!bs.exists()||bs.data().importing)
   throw new Error('據點不存在或正在匯入，請稍後再試');

  if(!ps.exists())return;

  if(ps.data().status!=='pending')
   throw new Error('此筆已確認收款，請重新整理；如需更正收款請從異動紀錄撤銷');

  tx.delete(p);
  tx.update(b,{
   revision:bs.data().revision+1,
   updatedAt:serverTimestamp()
  });
 });

 return {};
}
'''

for name, content in changes.items():
    path = Path(name)
    backup = path.with_name(path.name + '.before-pending-delete')
    if not backup.exists():
        backup.write_text(
            path.read_text(encoding='utf-8'),
            encoding='utf-8'
        )
    path.write_text(content, encoding='utf-8')

print('已新增待收款刪除按鈕。請建置網站並發布更新後的 firestore.rules。')
