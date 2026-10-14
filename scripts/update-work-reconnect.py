from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
marker = 'storeasy-work-reconnect-v1'
files = {}

def once(s, old, new):
    if s.count(old) != 1:
        raise RuntimeError('版本不符，尚未寫入：' + old[:60])
    return s.replace(old, new, 1)

p = root / 'src/work-tasks.ts'
s = p.read_text(encoding='utf-8')
if marker not in s:
    start = s.index('export const isWorkQuota=')
    end = s.index('export const stamp=', start)
    s = s[:start] + """export const isWorkQuota=(error:any):boolean=>String(error?.code||'').includes('resource-exhausted')||/resource-exhausted|quota|額度/i.test(String(error?.message||error||''));
export function workError(error:any):string {
 if(typeof error==='string')return error;
 const code=String(error?.code||'unknown');
 const message=String(error?.message||'操作失敗');
 if(isWorkQuota(error))return `Firebase 回傳額度限制（${code}）：${message}。請按「重新連線」重試。`;
 if(code.includes('permission'))return `操作遭拒（${code}）：請確認最新 Firestore 規則已發布，且你仍有此據點權限。`;
 return `${message}（${code}）`;
}
""" + s[end:]
    s = once(
        s,
        ' const uid=auth.currentUser?.uid;\n',
        ' const [reconnect,setReconnect]=useState(0);\n const uid=auth.currentUser?.uid;\n'
    )
    s = once(
        s,
        '[uid,profile?.role,JSON.stringify(profile?.branchIds)]',
        '[uid,profile?.role,JSON.stringify(profile?.branchIds),reconnect]'
    )
    s = once(
        s,
        'return {tasks,reads,error,hasUnread:',
        "return {tasks,reads,error,retry:()=>{setError('');setReconnect(n=>n+1);},hasUnread:"
    )
    files[str(p)] = s + '\n// ' + marker + '\n'

p = root / 'src/WorkTasks.tsx'
s = p.read_text(encoding='utf-8')
if marker not in s:
    s = once(
        s,
        'error:loadError}:any)',
        'error:loadError,retry}:any)'
    )
    s = once(
        s,
        ' const historyCursor=useRef<any>(null);',
        ' const [reconnect,setReconnect]=useState(0);\n const historyCursor=useRef<any>(null);'
    )
    s = once(
        s,
        '[selected,task?.deleted,global]',
        '[selected,task?.deleted,global,reconnect]'
    )
    s = once(
        s,
        '[selected,thread,task?.deleted,Boolean(item),item?.deleted,messageLimit]',
        '[selected,thread,task?.deleted,Boolean(item),item?.deleted,messageLimit,reconnect]'
    )
    s = once(
        s,
        '<button disabled={busy||quotaBlocked||!draft.trim()}>',
        '<button disabled={busy||!draft.trim()}>'
    )
    s = once(
        s,
        '{workError(error||loadError)}</div>',
        """{workError(error||loadError)} <button type="button" disabled={busy} onClick={()=>{setError('');setNotice('');retry?.();setReconnect(n=>n+1);}}>重新連線</button></div>"""
    )
    files[str(p)] = s + '\n// ' + marker + '\n'

p = root / 'src/main.tsx'
s = p.read_text(encoding='utf-8')
if marker not in s:
    s = once(
        s,
        'useWorkTasks, unreadThreads, isWorkQuota }',
        'useWorkTasks, unreadThreads, isWorkQuota, workError }'
    )
    pattern = r'if \(isWorkQuota\((\w+)\)\) return "Firebase 額度已用完，暫時無法讀取或儲存資料。請等額度重置後再試。";'
    s, count = re.subn(
        pattern,
        lambda m: 'if (isWorkQuota(' + m.group(1) + ')) return workError(' + m.group(1) + ');',
        s
    )
    if count != 1:
        raise RuntimeError('找不到原本的額度提示，尚未寫入')
    files[str(p)] = s + '\n// ' + marker + '\n'

for name, content in files.items():
    Path(name).write_text(content, encoding='utf-8')
    print('已更新 ' + name)

print('完成：可手動重送或重新連線，保留輸入文字，顯示實際錯誤碼。本次不需要修改 Firebase 規則。')
