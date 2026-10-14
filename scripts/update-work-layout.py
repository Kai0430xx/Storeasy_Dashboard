from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
marker = 'storeasy-work-polish-v1'
files = {}

def once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError('版本不符，尚未寫入：' + old[:60])
    return text.replace(old, new, 1)

p = root / 'src/work-tasks.ts'
s = p.read_text(encoding='utf-8')
if marker not in s:
    helpers = """export const isWorkQuota=(error:any):boolean=>String(error?.code||'').includes('resource-exhausted')||/quota|額度已用完/i.test(String(error?.message||error||''));
export function workError(error:any):string {
 if(isWorkQuota(error))return 'Firebase 額度已用完，暫時無法讀取或儲存資料。請等額度重置後重新整理再試；目前輸入的訊息尚未送出，會保留在輸入框。';
 if(String(error?.code||error?.message||'').includes('permission'))return '操作遭拒：請確認最新 Firestore 規則已發布，且你仍有此據點權限。';
 return String(error?.message||error||'操作失敗，請稍後再試');
}
"""
    s = once(s, 'export const stamp=', helpers + 'export const stamp=')
    s = s.replace('setError(e.message)', 'setError(workError(e))')
    files[str(p)] = s + '\n// ' + marker + '\n'

p = root / 'src/WorkTasks.tsx'
s = p.read_text(encoding='utf-8')
if marker not in s:
    s = once(s, 'unreadThreads,stamp}', 'unreadThreads,stamp,workError,isWorkQuota}')
    s = once(
        s,
        'const inactive=!task||task.deleted||item?.deleted;',
        'const inactive=!task||task.deleted||item?.deleted;\n const quotaBlocked=isWorkQuota(error)||isWorkQuota(loadError);'
    )
    s = s.replace('setError(e.message)', 'setError(workError(e))')
    s = once(
        s,
        "document.visibilityState==='visible'&&item",
        "document.visibilityState==='visible'&&!quotaBlocked&&item"
    )
    s = once(
        s,
        'if(task&&!dialog&&item&&(!task.deleted)',
        'if(task&&!dialog&&!quotaBlocked&&item&&(!task.deleted)'
    )
    s = once(
        s,
        '[selected,thread,otherLatest,Boolean(dialog),inactive]',
        '[selected,thread,otherLatest,Boolean(dialog),inactive,quotaBlocked]'
    )
    s = once(
        s,
        '[task,thread,dialog,inactive,reads]',
        '[task,thread,dialog,inactive,reads,quotaBlocked]'
    )
    s = once(
        s,
        "setError(e.message?.includes('permission')?'操作遭拒：請確認最新 Firestore 規則已發布，且你仍有此據點權限。':e.message)",
        'setError(workError(e))'
    )
    s = once(s, '{error||loadError}</div>', '{workError(error||loadError)}</div>')
    s = once(
        s,
        '<button disabled={busy||!draft.trim()}>傳送</button>',
        "<button disabled={busy||quotaBlocked||!draft.trim()}>{busy?'傳送中…':'傳送'}</button>"
    )

    start = s.index('<fieldset><legend>選擇據點</legend>')
    end = s.index('</fieldset>', start) + len('</fieldset>')
    replacement = """<fieldset className="work-branch-fieldset"><legend>選擇據點</legend>{form.mode==='single'?<label>據點<select aria-label="選擇任務據點" required value={form.branchIds[0]||''} onChange={e=>setForm({...form,branchIds:e.target.value?[e.target.value]:[]})}><option value="">請選擇一個據點</option>{branches.map((b:WorkRow)=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label>:<><div className="work-branch-toolbar"><span>已選 {form.branchIds.length}／{branches.length} 間</span><button type="button" className="text-button" onClick={()=>setForm({...form,branchIds:form.branchIds.length===branches.length?[]:branches.map((b:WorkRow)=>b.id)})}>全選／取消全選</button></div><div className="work-branch-options">{branches.map((b:WorkRow)=><label key={b.id} className={form.branchIds.includes(b.id)?'chosen':''}><input type="checkbox" name="work-branch" checked={form.branchIds.includes(b.id)} onChange={e=>setForm({...form,branchIds:e.target.checked?[...form.branchIds,b.id]:form.branchIds.filter((id:string)=>id!==b.id)})}/><span>{b.name}</span></label>)}</div></>}</fieldset>"""
    s = s[:start] + replacement + s[end:]
    files[str(p)] = s + '\n// ' + marker + '\n'

p = root / 'src/work-tasks.css'
s = p.read_text(encoding='utf-8')
if marker not in s:
    files[str(p)] = s + '\n' + """/* storeasy-work-polish-v1 */
.modal.wide.work-dialog{width:min(900px,94vw);max-height:94dvh}
.modal.work-dialog .work-branch-fieldset{max-height:none;overflow:visible;padding:16px;margin:16px 0}
.modal.work-dialog .work-branch-fieldset>label{margin:0}
.work-branch-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px;font-size:13px;color:#647692}
.modal.work-dialog .work-branch-options{grid-template-columns:repeat(2,minmax(0,1fr));max-height:38dvh;overflow:auto;padding:2px 6px 2px 2px;gap:8px}
.modal.work-dialog .work-branch-options label{display:flex;flex-direction:row;justify-content:flex-start;gap:10px;min-width:0;min-height:46px;padding:10px 12px;margin:0;border:1px solid #dce5f1;border-radius:8px;background:#fff;cursor:pointer}
.modal.work-dialog .work-branch-options label.chosen{background:#edf3fe;border-color:#8ca9d7}
.modal.work-dialog .work-branch-options input{width:18px;min-width:18px;height:18px;flex:0 0 18px;margin:0;padding:0;accent-color:#173f75}
.modal.work-dialog .work-branch-options span{flex:1;min-width:0;white-space:nowrap;line-height:1.5;overflow:hidden;text-overflow:ellipsis}
@media(max-width:540px){.modal.work-dialog{padding:18px}.modal.work-dialog .work-branch-options{grid-template-columns:1fr;max-height:40dvh}.work-branch-toolbar{flex-wrap:wrap}}
"""

p = root / 'src/main.tsx'
s = p.read_text(encoding='utf-8')
if marker not in s:
    s = once(
        s,
        'useWorkTasks, unreadThreads }',
        'useWorkTasks, unreadThreads, isWorkQuota }'
    )
    pattern = r'const friendly = \((\w+): any\) => \{'

    def replacement(m):
        return m.group() + '\n  if (isWorkQuota(' + m.group(1) + ')) return "Firebase 額度已用完，暫時無法讀取或儲存資料。請等額度重置後再試。";'

    s, count = re.subn(pattern, replacement, s)
    if count != 1:
        raise RuntimeError('找不到錯誤訊息處理位置，尚未寫入')
    files[str(p)] = s + '\n// ' + marker + '\n'

for name, content in files.items():
    Path(name).write_text(content, encoding='utf-8')
    print('已更新 ' + name)

print('完成：據點選擇版面與額度錯誤提示已更新。本次不需要修改 Firebase 規則。')
