from pathlib import Path
import re

if Path('src/work-branches.ts').exists():
    print('跨據點事項功能已套用。')
    raise SystemExit(0)

changes = {}

def edit(name, pattern, replacement):
    text = changes.get(name, Path(name).read_text(encoding='utf-8'))
    text, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise SystemExit(f'版本不符：{name}，尚未寫入任何檔案。')
    changes[name] = text

edit(
    'src/main.tsx',
    r'<WorkTasks profile=\{profile\} branches=',
    '<WorkTasks profile={profile} directoryBranches={branches} branches='
)

edit(
    'src/WorkTasks.tsx',
    r'(\{profile,\s*branches,)(\s*branchId)',
    r'\1directoryBranches=branches,\2'
)

edit(
    'src/WorkTasks.tsx',
    r'const people=useWorkPeople\(profile,peopleUsers\);',
    'const people=useWorkPeople(profile,peopleUsers);\n'
    ' const directory=useWorkBranches(profile,directoryBranches);\n'
    ' const taskBranches=directory.branches;'
)

edit(
    'src/WorkTasks.tsx',
    r'branchNames:Object\.fromEntries\(branches\.map',
    'branchNames:Object.fromEntries(taskBranches.map'
)

edit(
    'src/WorkTasks.tsx',
    r'setNotice\(`已發布 \$\{count\} 份事項`\);',
    "setNotice(`已發布 ${count} 份事項`);onSelectBranch?.('all');"
)

edit(
    'src/WorkTasks.tsx',
    r'\{categories\.error&&',
    '{directory.error&&<div className="alert error" role="alert">'
    '{directory.error}</div>}{categories.error&&'
)

text = changes['src/WorkTasks.tsx']
start = text.index("{dialog.kind==='create'&&<>")
end = text.index("{dialog.kind==='messageEdit'", start)

part = text[start:end]
part = part.replace('branches.map', 'taskBranches.map')
part = part.replace('branches.length', 'taskBranches.length')
part = part.replace(
    "{!global?' 可選擇你所屬的據點。':''}",
    '可選擇所有據點，建立者也能持續追蹤。'
)

changes['src/WorkTasks.tsx'] = (
    'import {useWorkBranches} from "./work-branches";\n'
    + text[:start] + part + text[end:]
)

edit(
    'src/work-tasks.ts',
    r'scopes\.forEach\(\(q,i\)=>',
    "if(profile.role==='manager')scopes.push(query("
    "collection(db,'workTasks'),where('createdBy','==',uid)));\n"
    "  scopes.forEach((q,i)=>"
)

edit(
    'firestore.rules',
    r'globalAccess\(\)\s*\|\|\s*d\.branchIds\.hasAny',
    'globalAccess() || d.createdBy==request.auth.uid || d.branchIds.hasAny'
)

edit(
    'firestore.rules',
    r'\s*&&\s*\(globalAccess\(\)\s*\|\|\s*profile\(\)'
    r'\.branchIds\.hasAll\(request\.resource\.data\.branchIds\)\)',
    ''
)

edit(
    'firestore.rules',
    r'match /workPeople/\{uid\} \{',
    r'''
// storeasy-work-branches-v1
match /workBranches/{id} {
 allow read: if workUser();
 allow create,update: if workUser() && branchAccess(id)
  && request.resource.data.keys().hasOnly(['name','archived'])
  && request.resource.data.name==getAfter(/databases/$(database)/documents/branches/$(id)).data.name
  && request.resource.data.archived==getAfter(/databases/$(database)/documents/branches/$(id)).data.get('archived',false);
 allow delete: if false;
}
match /workPeople/{uid} {
'''
)

changes['src/work-branches.ts'] = r'''
import {useEffect,useRef,useState} from 'react';
import {collection,doc,onSnapshot,writeBatch} from 'firebase/firestore';
import {db} from './firebase';
import {compareBranches} from './branch-order.js';
import {WorkRow,workError} from './work-tasks';

export function useWorkBranches(profile:WorkRow,owned:WorkRow[]){
 const [rows,setRows]=useState<WorkRow[]>([]);
 const [ready,setReady]=useState(false);
 const [error,setError]=useState('');
 const [version,setVersion]=useState(0);
 const syncing=useRef(false);

 useEffect(()=>{
  setRows([]);
  setReady(false);
  setError('');
  return onSnapshot(
   collection(db,'workBranches'),
   {includeMetadataChanges:true},
   s=>{
    setRows(s.docs.map(d=>({id:d.id,...d.data()})));
    if(!s.metadata.fromCache)setReady(true);
   },
   e=>setError(workError(e))
  );
 },[profile.role]);

 const sourceKey=JSON.stringify(
  owned.map(b=>[b.id,b.name,!!b.archived])
 );
 const rowsKey=JSON.stringify(
  rows.map(b=>[b.id,b.name,!!b.archived])
 );

 useEffect(()=>{
  if(!ready||syncing.current)return;
  const known=new Map(rows.map(b=>[b.id,b]));
  const missing=owned.filter(b=>
   known.get(b.id)?.name!==b.name
   ||!!known.get(b.id)?.archived!==!!b.archived
  );
  if(!missing.length)return;

  syncing.current=true;
  (async()=>{
   let success=false;
   try{
    for(let i=0;i<missing.length;i+=10){
     const batch=writeBatch(db);
     for(const b of missing.slice(i,i+10)){
      batch.set(doc(db,'workBranches',b.id),{
       name:b.name,
       archived:!!b.archived
      });
     }
     await batch.commit();
    }
    success=true;
    setError('');
   }catch(e){
    setError(workError(e));
   }finally{
    syncing.current=false;
    if(success)setVersion(n=>n+1);
   }
  })();
 },[sourceKey,rowsKey,ready,version]);

 const all=new Map(rows.map(b=>[b.id,b]));
 for(const b of owned)all.set(b.id,b);

 return {
  branches:[...all.values()]
   .filter(b=>!b.archived)
   .sort(compareBranches),
  error,
  ready
 };
}
'''.lstrip()

for name, content in changes.items():
    path = Path(name)
    backup = path.with_name(path.name + '.before-cross-branch-tasks')
    if path.exists() and not backup.exists():
        backup.write_text(
            path.read_text(encoding='utf-8'),
            encoding='utf-8'
        )
    path.write_text(content, encoding='utf-8')

print('已開放店長跨店建立事項。請發布 firestore.rules，並同步據點清單。')
