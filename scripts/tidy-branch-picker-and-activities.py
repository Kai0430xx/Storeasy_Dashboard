from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
changes = {}

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
 const extraCount=rest.filter(b=>selected.includes(b.id)).length+(other?1:0);

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
    <p className="waiting-branch-group-title">權限內據點</p>
    {options(mine)}
   </>}

   {!mine.length && !global &&
    <p className="hint">
     目前沒有指派的所屬據點，可展開下方清單選擇。
    </p>
   }

   <details className="waiting-other-branches">
    <summary>
     其餘據點
     <span>已選 {extraCount}</span>
    </summary>

    {rest.length>0 && options(rest)}

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
     不在系統內的據點，請勾選「其它據點」並自行填寫名稱。
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
   </details>
  </fieldset>
 );
}
'''

p = root / 'src/main.tsx'
s = p.read_text(encoding='utf-8')

if 'import ActivityOverviewDisclosure from' not in s:
    title = s.find('<h2>活動使用概況</h2>')
    start = s.rfind('<section className="panel">', 0, title)
    end = s.find('</section>', title)

    if title < 0 or start < 0 or end < 0:
        raise SystemExit('找不到完整活動使用概況，未變更檔案')

    end += len('</section>')
    s = (
        s[:start]
        + '<ActivityOverviewDisclosure key={"activities-"+branchId} '
        + 'collapsed={branchId === "all"}>'
        + s[start:end]
        + '</ActivityOverviewDisclosure>'
        + s[end:]
    )
    s = (
        'import ActivityOverviewDisclosure '
        'from "./ActivityOverviewDisclosure";\n'
        + s
    )

changes['src/main.tsx'] = s

changes['src/ActivityOverviewDisclosure.tsx'] = '''import type {ReactNode} from 'react';
import './activity-overview-disclosure.css';

export default function ActivityOverviewDisclosure({
 collapsed,children
}: {
 collapsed:boolean;
 children:ReactNode;
}) {
 if(!collapsed)return <>{children}</>;

 return (
  <details className="panel activity-overview-disclosure">
   <summary>活動使用概況</summary>
   <div className="activity-overview-disclosure-body">
    {children}
   </div>
  </details>
 );
}
'''

changes['src/activity-overview-disclosure.css'] = '''
.activity-overview-disclosure {
  padding:0;
}
.activity-overview-disclosure > summary {
  padding:18px 24px;
  font-weight:600;
  cursor:pointer;
}
.activity-overview-disclosure > summary:focus-visible {
  outline:2px solid #204b80;
  outline-offset:-4px;
  border-radius:10px;
}
.activity-overview-disclosure-body {
  padding:0 24px 24px;
}
.activity-overview-disclosure-body > .panel {
  margin:0;
  border:0;
  box-shadow:none;
}
.activity-overview-disclosure-body .panel-heading {
  padding:0 0 16px;
}
.activity-overview-disclosure-body .panel-heading h2 {
  display:none;
}
.activity-overview-disclosure-body .activity-summary {
  padding:0;
}
'''

p = root / 'src/manual-waiting.ts'
s = p.read_text(encoding='utf-8')

old = '候補據點可複選；自己的所屬據點優先顯示，其它系統據點預設收合，點標題展開後勾選。候補不在系統內的據點時，勾選「其它據點」並填名稱，多間可用頓號分隔。'
new = '候補據點可複選；外面優先顯示店長權限內的所有據點。其餘系統據點與自行輸入的「其它據點」都在收合區內，點「其餘據點」標題展開後選擇或填寫名稱，多間可用頓號分隔。'

if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    previous = new.replace(
        '點「其餘據點」標題',
        '點「其它據點」標題',
    )
    if previous in s:
        s = s.replace(previous, new, 1)
    else:
        raise SystemExit('找不到候補據點手冊說明，未變更檔案')

old = '「業績去年同月比較」、「每月目標」及「年度目標」各自預設收合'
new = '「業績去年同月比較」、「活動使用概況」、「每月目標」及「年度目標」各自預設收合'

if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit('找不到總覽收合手冊說明，未變更檔案')

changes['src/manual-waiting.ts'] = s

p = root / 'src/manual-content.ts'
s = p.read_text(encoding='utf-8')

old = '在「活動使用概況」點活動名稱，開啟使用明細。'
new = '查看全部據點時，先展開「活動使用概況」，再點活動名稱開啟使用明細；單一據點直接顯示。'

if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit('找不到活動使用手冊說明，未變更檔案')

changes['src/manual-content.ts'] = s

p = root / 'src/WaitingList.tsx'
s = p.read_text(encoding='utf-8')

if 'setSavedNotice' not in s:
    if s.count('setSelected(id);') != 1:
        raise SystemExit('找不到儲存後開啟明細的程式，未變更檔案')

    s = s.replace(
        'setSelected(id);',
        "setSelected(null);setSavedNotice('候補已儲存');",
        1,
    )
    s, count = re.subn(
        r'const id\s*=\s*await saveWaiting\(',
        'await saveWaiting(',
        s,
        count=1,
    )
    if count != 1:
        raise SystemExit('找不到候補儲存入口，未變更檔案')

    anchor = 'const names=new Map'
    if s.count(anchor) != 1:
        raise SystemExit('找不到候補狀態位置，未變更檔案')

    s = s.replace(
        anchor,
        "const [savedNotice,setSavedNotice]=useState('');\n"
        " const names=new Map",
        1,
    )

    notice = '''{savedNotice&&!edit&&<div className="alert success" role="status">{savedNotice}<button aria-label="關閉儲存提示" onClick={()=>setSavedNotice('')}>×</button></div>}'''

    s, count = re.subn(
        r'(return\s*<>)',
        lambda m: m.group(0) + '\n  ' + notice,
        s,
        count=1,
    )
    if count != 1:
        raise SystemExit('找不到候補畫面，未變更檔案')

    s = re.sub(
        r'(const (?:startEdit|open)=\([^)]*\)=>\{)',
        lambda m: m.group(0) + "setSavedNotice('');",
        s,
    )

changes['src/WaitingList.tsx'] = s

s = changes['src/manual-waiting.ts']
old = '按「確認儲存」後建立候補紀錄，不會新增租約或計入業績。'
new = '按「確認儲存」後會關閉視窗、回到候補列表並顯示「候補已儲存」，不自動開啟明細。要查看合適空倉時，再點該筆紀錄；建立候補不會新增租約或計入業績。'

if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit('找不到候補儲存手冊說明，未變更檔案')

changes['src/manual-waiting.ts'] = s

for name, text in changes.items():
    target = root / name

    if target.exists():
        backup = (
            root / '.update-backups'
            / 'branch-picker-activities-v1' / name
        )
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_text(
                target.read_text(encoding='utf-8'),
                encoding='utf-8',
            )

    target.write_text(text, encoding='utf-8')

print('已更新候補據點收合、儲存返回列表及活動概況收合，並同步操作手冊')
