from pathlib import Path
import re

marker = '// storeasy-display-cleanup-v1'
changes = {}

def read(name):
    return Path(name).read_text(encoding='utf-8')

name = 'src/main.tsx'
s = read(name)

if marker not in s:
    s, headings = re.subn(
        r'<th>空倉起始日</th>',
        '{status === "vacant" && <th>空倉起始日</th>}',
        s
    )
    s, cells = re.subn(
        r'<td>\s*<VacancyCell\s+unit=\{(\w+)\}'
        r'\s+editable=\{Boolean\(canWrite\)\}\s*/>\s*</td>',
        r'{status === "vacant" && <td><VacancyCell '
        r'unit={\1} editable={Boolean(canWrite)} /></td>}',
        s
    )

    if (headings, cells) != (1, 1):
        raise SystemExit('倉位表格版本不符，尚未修改任何檔案。')

    changes[name] = s + '\n' + marker + '\n'

name = 'src/YearGoalsView.tsx'
s = read(name)
s = re.sub(
    r"r\.referrals\s*==\s*null\s*\?\s*'未填'",
    "r.referrals==null?''",
    s
)
s = re.sub(
    r"r\.referrals\s*\?\?\s*'未填'",
    "r.referrals??''",
    s
)
changes[name] = s

name = 'src/annual-export.ts'
if Path(name).exists():
    s = read(name)
    s = re.sub(
        r"r\.referrals\s*\?\?\s*'未填'",
        "r.referrals??''",
        s
    )
    changes[name] = s

changes['src/LightInsights.tsx'] = r'''
import {useEffect,useState} from 'react';
import {collection,getDocs,query,where} from 'firebase/firestore';
import {db} from './firebase';
import {exitCategories,vacantDays} from './targets.js';
import {taipeiDate} from './domain.js';

type Row=Record<string,any>;

export default function LightInsights(
 {branches,events,month}:
 {branches:Row[];events:Row[];month:string}
){
 const [units,setUnits]=useState<Row[]|null>(null);
 const [error,setError]=useState('');
 const scope=JSON.stringify(
  branches.map(b=>[b.id,Number(b.vacant||0)])
 );

 useEffect(()=>{
  let active=true;
  setUnits(null);
  setError('');

  const selected=JSON.parse(scope) as [string,number][];

  Promise.all(
   selected.filter(([,count])=>count>0).map(async([id])=>{
    const snapshot=await getDocs(query(
     collection(db,'branches',id,'units'),
     where('status','==','vacant')
    ));
    return snapshot.docs.map(d=>d.data());
   })
  ).then(rows=>{
   if(active)setUnits(rows.flat());
  }).catch(e=>{
   if(active)setError(e instanceof Error?e.message:String(e));
  });

  return()=>{active=false;};
 },[scope]);

 const vacant=units?.filter(
  u=>u.status==='vacant'&&!u.archived&&!u.missing
 );
 const today=taipeiDate();
 const count=(days:number)=>vacant?.filter(
  u=>(vacantDays(u,today)??-1)>=days
 ).length;
 const exits=events.filter(e=>e.type==='exit'&&!e.voided);

 return <section
  className="panel target-panel"
  aria-label="空倉與退租概況"
 >
  <h2>空倉與退租概況</h2>
  <p>
   目前空倉 {branches.reduce(
    (n,b)=>n+Number(b.vacant||0),0
   )} 間
  </p>

  {error?<p role="alert">{error}</p>:vacant?<>
   <p>
    空置至少 30 天：{count(30)} 間・
    至少 60 天：{count(60)} 間・
    至少 90 天：{count(90)} 間（區間包含較長天數）
   </p>
   {vacant.some(u=>vacantDays(u,today)==null)&&
    <p className="hint">
     起始日未記錄：{
      vacant.filter(u=>vacantDays(u,today)==null).length
     } 間
    </p>
   }
  </>:<p role="status">載入空倉天數統計中…</p>}

  <h3>{month} 退租原因</h3>
  {[...exitCategories,'未分類'].map(c=>
   <span className="badge" key={c}>
    {c}：{
     exits.filter(e=>(e.exitCategory||'未分類')===c).length
    } 筆{' '}
   </span>
  )}
 </section>;
}
'''.lstrip()

for name, content in changes.items():
    path = Path(name)
    backup = path.with_name(path.name + '.before-display-cleanup')
    if path.exists() and not backup.exists():
        backup.write_text(
            path.read_text(encoding='utf-8'),
            encoding='utf-8'
        )
    path.write_text(content, encoding='utf-8')

print('已調整轉介留白、空倉欄位與概況自動顯示。')
