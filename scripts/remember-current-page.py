from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
changes = {}

hook = '''import {useCallback,useEffect,useState} from 'react';

const pages = ['dashboard','units','activities','imports','targets','waiting','work','users','manual'];

function readPage(){
 const page = window.location.hash.slice(1);
 return pages.includes(page) ? page : 'dashboard';
}

function allowed(page:string,role:string){
 if(role==='pending')return ['dashboard','manual'].includes(page);
 if(page==='users')return ['admin','supervisor'].includes(role);
 if(['waiting','work'].includes(page))return ['admin','supervisor','manager'].includes(role);
 return pages.includes(page);
}

export function usePageNavigation(role?:string){
 const [page,setPage] = useState(readPage);

 useEffect(()=>{
  const sync = ()=>setPage(readPage());
  window.addEventListener('hashchange',sync);
  return ()=>window.removeEventListener('hashchange',sync);
 },[]);

 useEffect(()=>{
  if(!role)return;
  const next = allowed(page,role) ? page : 'dashboard';
  if(next!==page)setPage(next);
  if(window.location.hash!=='#'+next){
   window.history.replaceState(
    null,'',
    window.location.pathname+window.location.search+'#'+next
   );
  }
 },[page,role]);

 const navigate = useCallback((next:string)=>{
  const target = pages.includes(next) && (!role || allowed(next,role))
   ? next : 'dashboard';
  setPage(target);
  if(window.location.hash!=='#'+target)window.location.hash=target;
 },[role]);

 return [page,navigate] as const;
}
'''

p = root / 'src/main.tsx'
s = p.read_text(encoding='utf-8')

if 'import {usePageNavigation}' not in s:
    s, count = re.subn(
        r'\[page,\s*setPage\]\s*=\s*useState\(["\']dashboard["\']\)',
        '[page, setPage] = usePageNavigation(profile?.role)',
        s,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到分頁狀態，未更動任何檔案。')
    s = 'import {usePageNavigation} from "./page-navigation";\n' + s

changes['src/main.tsx'] = s
changes['src/page-navigation.ts'] = hook

p = root / 'src/manual-content.ts'
s = p.read_text(encoding='utf-8')

if '重新整理保留目前分頁' not in s:
    topic = '''
   {
    title:"重新整理保留目前分頁",
    steps:[
     "從左側選擇頁面後，重新整理會留在目前分頁，不再回到營運總覽。",
     "可使用瀏覽器上一頁與下一頁切換已瀏覽的分頁。",
     "此功能保留分頁位置，不會保存尚未送出的表單；重新整理前請先儲存。"
    ],
    result:"登入後仍依目前帳號權限顯示；無權限或無效的分頁會回到營運總覽。據點與月份篩選仍依原本規則初始化。"
   },
'''
    s, count = re.subn(
        r'((?:"id"|id)\s*:\s*["\']dashboard["\'][\s\S]*?(?:"topics"|topics)\s*:\s*\[)',
        lambda m: m.group(1) + topic,
        s,
        count=1
    )
    if count != 1:
        raise SystemExit('找不到操作手冊章節，未更動任何檔案。')

changes['src/manual-content.ts'] = s

p = root / 'src/waiting-list.css'
s = p.read_text(encoding='utf-8')

if '/* waiting-status-one-row-v1 */' not in s:
    s += '''
/* waiting-status-one-row-v1 */
.modal fieldset.waiting-detail-status {
 min-width:0;
}

.waiting-detail-status > .waiting-status-tabs {
 display:grid;
 grid-template-columns:repeat(5,minmax(max-content,1fr));
 gap:8px;
 overflow-x:auto;
 padding-bottom:4px;
}

.waiting-detail-status .waiting-status-tabs > label {
 white-space:nowrap;
 padding:10px 8px;
 gap:6px;
 justify-content:center;
}
'''

changes['src/waiting-list.css'] = s

p = root / 'src/manual-waiting.ts'
s = p.read_text(encoding='utf-8')

if '五個狀態同一排' not in s:
    old = '同時只能勾選一項'
    if old not in s:
        raise SystemExit('請先完成前一次候補更新，未更動任何檔案。')
    s = s.replace(
        old,
        '五個狀態同一排顯示，手機空間不足可左右滑動；同時只能勾選一項',
        1
    )

changes['src/manual-waiting.ts'] = s

for name, content in changes.items():
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')

print('完成：保留目前分頁、候補五個狀態同排，操作手冊已同步更新。')
