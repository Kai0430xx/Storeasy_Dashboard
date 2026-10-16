from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
changes = {}

p = root / 'src/main.tsx'
s = p.read_text(encoding='utf-8')

if 'function closeAppModal()' not in s:
    s, count = re.subn(
        r'waitingId:\s*unit\.waitingId',
        'waitingId:unit.waitingId, waitingReturn:{branchId,month,search,status}',
        s,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到候補承租來源，未更動檔案。')

    anchor = '  const stats = (targetMonth: string) => {'
    if anchor not in s:
        raise SystemExit('找不到主頁定位，未更動檔案。')

    s = s.replace(anchor, '''
  function closeAppModal(){
    if(busy)return;
    const waitingId=modal?.kind==="event"&&modal.type==="new"?
     modal.waitingId:null;
    const context=modal?.waitingReturn;

    setModal(null);
    setError("");

    if(waitingId){
      setBranchId(context?.branchId||"all");
      if(context?.month)setMonth(context.month);
      setSearch(context?.search||"");
      setStatus(context?.status||"all");
      setWaitingFocus(waitingId);
      setPage("waiting");
    }
  }
''' + anchor, 1)

    s, count = re.subn(
        r'onClick=\{\(\)\s*=>\s*setModal\(null\)\}',
        'onClick={closeAppModal}',
        s,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到視窗關閉按鈕，未更動檔案。')

changes['src/main.tsx'] = s

p = root / 'src/BranchCheers.tsx'
s = p.read_text(encoding='utf-8')

if 'cheer-preview-block' not in s:
    pattern = (
        r'<div className="cheer-preview" aria-label="信心喊話預覽">'
        r'\s*<CheerText text=\{text\.trim\(\)\}/>\s*</div>'
    )
    replacement = '''
    <div className="cheer-preview-block">
     <h3>頁面頂端預覽</h3>
     <div
      className={'cheer-preview'+(text.trim()?' has-text':'')}
      aria-label="信心喊話預覽"
     >
      {text.trim()?
       <CheerText text={text.trim()}/>:
       <span className="cheer-preview-empty">
        輸入文字後，這裡會顯示大聲公與喊話樣式。
       </span>
      }
     </div>
    </div>'''
    s, count = re.subn(
        pattern, lambda m: replacement, s, count=1
    )
    if count != 1:
        raise SystemExit('找不到喊話預覽區，未更動檔案。')

if 'cheer-configured-grid' not in s:
    s = s.replace(
        '{doc,onSnapshot,',
        '{collection,doc,onSnapshot,',
        1
    )
    anchor = 'const dirty=useRef(false)'
    if anchor not in s:
        raise SystemExit('找不到喊話設定狀態，未更動檔案。')

    state = '''
 const [configured,setConfigured]=useState<Record<string,string>>({});
 const [configuredReady,setConfiguredReady]=useState(false);
 const [configuredError,setConfiguredError]=useState('');

 useEffect(()=>onSnapshot(
  collection(db,'branchCheers'),
  snapshot=>{
   setConfigured(Object.fromEntries(
    snapshot.docs.map(d=>[d.id,d.data().text||''])
   ));
   setConfiguredReady(true);
   setConfiguredError('');
  },
  e=>{
   setConfiguredError(e.message);
   setConfiguredReady(false);
  }
 ),[]);

 const configuredBranches=available.filter(
  b=>configured[b.id]?.trim()
 );
'''
    s = s.replace(anchor, state + anchor, 1)

    if '</form>' not in s:
        raise SystemExit('找不到喊話表單，未更動檔案。')

    section = '''
   <section className="cheer-configured" aria-label="已設定的據點">
    <h3>
     已設定的據點
     {configuredReady&&<span> {configuredBranches.length} 間</span>}
    </h3>

    {configuredError?
     <p role="alert" className="alert error">
      無法載入已設定清單：{configuredError}
     </p>:
     !configuredReady?<p>載入中…</p>:
     !configuredBranches.length?
      <p className="hint">目前沒有已設定喊話的據點。</p>:
      <div className="cheer-configured-grid">
       {configuredBranches.map(b=>
        <article key={b.id}>
         <div>
          <strong>{b.name}</strong>
          <button
           type="button"
           className="text-button"
           aria-label={'編輯 '+b.name+' 信心喊話'}
           disabled={busy}
           onClick={()=>{
            if(b.id!==id&&dirty.current&&!window.confirm(
             '尚有未儲存的文字，確定切換據點？'
            ))return;
            setSelected(b.id);
            window.scrollTo({top:0,behavior:'smooth'});
           }}
          >編輯</button>
         </div>
         <p>{configured[b.id]}</p>
        </article>
       )}
      </div>
    }
   </section>'''
    s = s.replace('</form>', '</form>\n' + section, 1)

changes['src/BranchCheers.tsx'] = s

p = root / 'src/branch-cheers.css'
s = p.read_text(encoding='utf-8')

if '/* cheer-editor-layout-v2 */' not in s:
    s += '''
/* cheer-editor-layout-v2 */
.cheer-editor {
 width:100%;
 max-width:920px;
 padding:28px;
}
.cheer-editor > .hint {
 margin:0 0 24px;
 line-height:1.7;
}
.cheer-editor > label {
 display:block;
 max-width:420px;
 margin:0 0 24px;
}
.cheer-editor form > label {
 display:block;
 margin:0;
}
.cheer-editor textarea {
 min-height:130px;
 margin-top:8px;
}
.cheer-editor form > .hint {
 margin:8px 0 24px;
}
.cheer-preview-block {
 margin:0 0 24px;
}
.cheer-preview-block h3 {
 font-size:14px;
 margin:0 0 10px;
}
.cheer-editor .cheer-preview {
 background:#f7f9fc;
 border-color:#dae3ed;
 margin:0;
 min-height:80px;
}
.cheer-editor .cheer-preview.has-text {
 background:#fff3c4;
 border-color:#f0d47a;
}
.cheer-preview-empty {
 color:#7a8799;
 font-size:14px;
 font-weight:400;
}
.cheer-editor .cheer-actions {
 margin-top:24px;
 padding-top:20px;
 border-top:1px solid #e3e9f1;
}
@media(max-width:600px){
 .cheer-editor { padding:20px; }
}
'''

if '/* cheer-configured-list-v1 */' not in s:
    s += '''
/* cheer-configured-list-v1 */
.cheer-configured {
 margin-top:32px;
 padding-top:24px;
 border-top:1px solid #e3e9f1;
}
.cheer-configured h3 {
 margin:0 0 16px;
 font-size:16px;
}
.cheer-configured h3 span {
 color:#718099;
 font-size:13px;
 font-weight:400;
}
.cheer-configured-grid {
 display:grid;
 grid-template-columns:repeat(2,minmax(0,1fr));
 gap:12px;
}
.cheer-configured-grid article {
 border:1px solid #dae3ed;
 border-radius:8px;
 padding:14px;
 min-width:0;
}
.cheer-configured-grid article > div {
 display:flex;
 align-items:center;
 justify-content:space-between;
 gap:12px;
}
.cheer-configured-grid strong {
 overflow-wrap:anywhere;
}
.cheer-configured-grid p {
 margin:10px 0 0;
 white-space:pre-wrap;
 overflow-wrap:anywhere;
 color:#516077;
}
@media(max-width:600px){
 .cheer-configured-grid {
  grid-template-columns:1fr;
 }
}
'''

changes['src/branch-cheers.css'] = s

p = root / 'src/manual-waiting.ts'
s = p.read_text(encoding='utf-8')

if '從候補開啟承租後按右上角 X' not in s:
    s = s.replace(
        '取消表單不會變更倉位或候補。',
        '從候補開啟承租後按右上角 X，會回到原候補明細及原據點範圍；'
        '直接從倉位管理開啟時，關閉仍留在倉位清單。'
        '取消表單不會變更倉位或候補。'
    )
changes['src/manual-waiting.ts'] = s

p = root / 'src/manual-content.ts'
s = p.read_text(encoding='utf-8')
s = s.replace(
    '預覽會顯示淡黃色底、深色文字與大聲公',
    '下方「頁面頂端預覽」會顯示淡黃色底、深色文字與大聲公'
)
s = s.replace(
    '留空儲存後，不會顯示文字、底色及大聲公。',
    '留空儲存後，不會顯示文字、底色及大聲公；'
    '設定頁空白預覽只顯示灰底提示。'
)
s = s.replace(
    '主管或管理員從左側點「信心喊話」，在設定據點選擇分店。',
    '主管或管理員從左側點「信心喊話」，下方「已設定的據點」'
    '會列出已儲存的據點、文字及總間數；點編輯可切換到該店，'
    '也可在設定據點選擇分店。'
)
changes['src/manual-content.ts'] = s

for name, content in changes.items():
    (root / name).write_text(content, encoding='utf-8')

print('完成：候補承租取消返回、喊話版面與已設定清單，手冊同步更新。')
