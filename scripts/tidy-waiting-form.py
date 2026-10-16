from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
changes = {}

p = root / 'src/WaitingList.tsx'
s = p.read_text(encoding='utf-8')

if 'import WaitingBranchPicker from' not in s:
    start = s.index('<fieldset className="waiting-branches">')
    end = s.index('</fieldset>', start) + len('</fieldset>')
    s = s[:start] + '''<WaitingBranchPicker
        key={edit.id || 'new'}
        branches={directory.branches}
        ownedIds={profile.branchIds || []}
        global={['admin','supervisor'].includes(profile.role)}
        selected={edit.branchIds}
        onChange={ids=>update('branchIds',ids)}
        other={other}
        onOtherChange={setOther}
        otherName={edit.otherBranches}
        onOtherNameChange={name=>update('otherBranches',name)}
       />''' + s[end:]
    s = 'import WaitingBranchPicker from "./WaitingBranchPicker";\n' + s

if 'className="modal wide waiting-editor"' not in s:
    s, count = re.subn(
        r'className="modal wide"(?=\s+role="dialog"\s+aria-modal="true"\s+aria-label=\{edit.id)',
        'className="modal wide waiting-editor"',
        s,
        count=1,
    )
    if count != 1:
        raise SystemExit('找不到候補編輯視窗，未變更檔案')

changes['src/WaitingList.tsx'] = s

changes['src/WaitingBranchPicker.tsx'] = '''type Branch = Record<string, any>;

export default function WaitingBranchPicker({
 branches,ownedIds,global,selected,onChange,
 other,onOtherChange,otherName,onOtherNameChange
}: {
 branches: Branch[];
 ownedIds: string[];
 global: boolean;
 selected: string[];
 onChange: (ids: string[])=>void;
 other: boolean;
 onOtherChange: (value: boolean)=>void;
 otherName: string;
 onOtherNameChange: (value: string)=>void;
}) {
 const mine=branches.filter(b=>ownedIds.includes(b.id));
 const rest=branches.filter(b=>!ownedIds.includes(b.id));
 const checkedRest=rest.filter(b=>selected.includes(b.id)).length;

 const options=(rows:Branch[]) => (
  <div className="waiting-branch-grid">
   {rows.map(b=>
    <label key={b.id}>
     <input
      type="checkbox"
      checked={selected.includes(b.id)}
      onChange={e=>onChange(
       e.target.checked
        ?[...selected,b.id]
        :selected.filter(id=>id!==b.id)
      )}
     />
     <span>{b.name}</span>
    </label>
   )}
  </div>
 );

 return (
  <fieldset className="waiting-branches">
   <legend>候補據點（可複選）</legend>

   {mine.length>0 && <>
    <p className="waiting-branch-group-title">所屬據點</p>
    {options(mine)}
   </>}

   {!mine.length && !global &&
    <p className="hint">
     目前沒有指派的所屬據點，可展開其它系統據點選擇。
    </p>
   }

   {rest.length>0 &&
    <details className="waiting-other-branches">
     <summary>
      其它系統據點
      <span>已選 {checkedRest}／{rest.length}</span>
     </summary>
     {options(rest)}
    </details>
   }

   <div className="waiting-branch-grid waiting-custom-branch">
    <label>
     <input
      type="checkbox"
      checked={other}
      onChange={e=>onOtherChange(e.target.checked)}
     />
     <span>其它據點</span>
    </label>
   </div>

   <p className="hint">
    候補不在系統內的據點時，勾選「其它據點」並自行填寫名稱。
   </p>

   {other &&
    <label>
     其它據點名稱
     <input
      required
      maxLength={300}
      placeholder="多個據點可用頓號分隔"
      value={otherName}
      onChange={e=>onOtherNameChange(e.target.value)}
     />
    </label>
   }
  </fieldset>
 );
}
'''

p = root / 'src/waiting-list.css'
s = p.read_text(encoding='utf-8')

if '/* waiting-form-layout-v2 */' not in s:
    s += '''
/* waiting-form-layout-v2 */
.modal.wide.waiting-editor {
  width:min(1100px, calc(100vw - 40px));
  max-height:94dvh;
  overflow-y:auto;
  box-sizing:border-box;
}
.waiting-editor form > fieldset.waiting-form {
  max-height:none;
  overflow:visible;
  border:0;
  padding:0;
  margin:0 0 18px;
}
.waiting-editor .waiting-branches,
.waiting-editor .waiting-range {
  max-height:none;
  overflow:visible;
}
.waiting-editor .waiting-branch-grid {
  max-height:none;
  overflow:visible;
  padding:4px 0;
  grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
}
.waiting-branch-group-title {
  font-weight:600;
  margin:0 0 8px;
}
.waiting-other-branches {
  border-top:1px solid #dae3ed;
  margin-top:12px;
}
.waiting-other-branches > summary {
  padding:14px 0;
  cursor:pointer;
  font-weight:600;
}
.waiting-other-branches > summary span {
  font-weight:400;
  color:#728198;
  margin-left:8px;
}
.waiting-custom-branch {
  margin-top:12px;
}
.waiting-editor textarea {
  min-height:72px;
}
@media(max-width:600px){
  .modal.wide.waiting-editor {
    width:calc(100vw - 24px);
    padding:20px;
  }
}
'''

changes['src/waiting-list.css'] = s

p = root / 'src/manual-waiting.ts'
s = p.read_text(encoding='utf-8')

old = '候補據點可複選網頁內所有據點；選「其它據點」後填名稱，多間可用頓號分隔。'
new = '候補據點可複選；自己的所屬據點優先顯示，其它系統據點預設收合，點標題展開後勾選。候補不在系統內的據點時，勾選「其它據點」並填名稱，多間可用頓號分隔。'

if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit('找不到候補據點操作說明，未變更檔案')

changes['src/manual-waiting.ts'] = s

p = root / 'src/main.tsx'
s = p.read_text(encoding='utf-8')

if '<GoalsOverview collapsible=' not in s:
    if s.count('<GoalsOverview') != 1:
        raise SystemExit('找不到唯一的總覽目標區塊，未變更檔案')
    s = s.replace(
        '<GoalsOverview',
        '<GoalsOverview collapsible={branchId === "all"}',
        1,
    )

changes['src/main.tsx'] = s

p = root / 'src/GoalsOverview.tsx'
s = p.read_text(encoding='utf-8')

if 'import GoalDisclosure from' not in s:
    s = 'import GoalDisclosure from "./GoalDisclosure";\n' + s

    before = 'month,global,onEdit}:{branches:'
    if before not in s:
        raise SystemExit('找不到目標元件參數，未變更檔案')

    s = s.replace(
        before,
        'month,global,onEdit,collapsible=false}:{branches:',
        1,
    )
    s = s.replace(
        'onEdit?:(v:Row)=>void})',
        'onEdit?:(v:Row)=>void;collapsible?:boolean})',
        1,
    )

    for component, title, period in [
        ('MonthlyGoalsTable', '每月目標', 'month'),
        ('AnnualGoalsTable', '年度目標', 'year'),
    ]:
        pattern = r'<' + component + r'\b[^>]*?/>'

        def wrap(match):
            return (
                '<GoalDisclosure key={"'
                + component + '-"+' + period
                + '} collapsed={collapsible} title={'
                + period + '+" ' + title + '"}>'
                + match.group(0)
                + '</GoalDisclosure>'
            )

        s, count = re.subn(pattern, wrap, s, count=1)
        if count != 1:
            raise SystemExit('找不到目標表格，未變更檔案')

changes['src/GoalsOverview.tsx'] = s

changes['src/GoalDisclosure.tsx'] = '''import type {ReactNode} from 'react';
import './goal-disclosure.css';

export default function GoalDisclosure({
 collapsed,title,children
}: {
 collapsed:boolean;
 title:string;
 children:ReactNode;
}) {
 if(!collapsed)return <>{children}</>;

 return (
  <details className="goal-disclosure">
   <summary>{title}</summary>
   <div className="goal-disclosure-content">
    {children}
   </div>
  </details>
 );
}
'''

changes['src/goal-disclosure.css'] = '''
.goal-disclosure {
  margin:16px 0;
  border:1px solid #dae3ed;
  border-radius:8px;
}
.goal-disclosure > summary {
  padding:16px;
  font-size:18px;
  font-weight:600;
  cursor:pointer;
}
.goal-disclosure > summary:focus-visible {
  outline:2px solid #204b80;
  outline-offset:-3px;
  border-radius:8px;
}
.goal-disclosure-content {
  padding:0 16px 16px;
}
.goal-disclosure-content > h3 {
  display:none;
}
'''

s = changes['src/manual-waiting.ts']
old = '選全部據點時，「各據點營運概況」及其後的「業績去年同月比較」預設收合，點標題展開。'
new = '選全部據點時，「各據點營運概況」、「業績去年同月比較」、「每月目標」及「年度目標」各自預設收合，點各標題展開；單一據點直接顯示。'

if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit('找不到總覽收合操作說明，未變更檔案')

changes['src/manual-waiting.ts'] = s

for name, text in changes.items():
    target = root / name
    if target.exists():
        backup = root / '.update-backups' / 'waiting-form-v2' / name
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_text(
                target.read_text(encoding='utf-8'),
                encoding='utf-8',
            )
    target.write_text(text, encoding='utf-8')

print('已改善候補表單、收合全部據點目標並同步操作手冊')
