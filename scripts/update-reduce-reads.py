from pathlib import Path
import base64, gzip, json, re

root = Path(__file__).resolve().parents[1]
files = {}

def read(name):
    return (root / name).read_text(encoding="utf-8")

def replace(s, old, new):
    if s.count(old) != 1:
        raise RuntimeError("替換位置不唯一：" + old[:80])
    return s.replace(old, new, 1)

def sub(s, pattern, replacement):
    s, count = re.subn(pattern, replacement, s, count=1)
    if count != 1:
        raise RuntimeError("找不到替換位置：" + pattern[:80])
    return s

def imports(s, names):
    def insert(m):
        current = [n.strip() for n in m[1].split(',')]
        added = [n for n in names if n not in current]
        return (
            'import { ' + ', '.join(current + added)
            + ' } from "firebase/firestore";'
        )
    return sub(
        s,
        r"import\s*\{([^}]+)\}\s*from\s*['\"]firebase/firestore['\"];?",
        insert,
    )

payload = """
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
"""

files.update(json.loads(gzip.decompress(base64.b64decode(payload))))

s = read("src/main.tsx")
if 'import LightInsights from "./LightInsights";' not in s:
    s = (
        'import LightInsights from "./LightInsights";\n'
        'import LazyUnits from "./LazyUnits";\n' + s
    )

    s = replace(
        s,
        '  const branches = [...branchRows].sort(compareBranches);',
        '  const [loadAllUnits,setLoadAllUnits]=useState(false);\n'
        '  const branches = [...branchRows].sort(compareBranches);',
    )

    s = replace(
        s,
        'if (page === "units" || page === "imports" || page === "activities" || page === "dashboard")',
        'if ((page === "units" && (branchId !== "all" || branches.filter(b=>!b.archived).length <= 1 || loadAllUnits)) || (page === "imports" && branchId !== "all"))',
    )

    s = sub(
        s,
        r'\[\s*"months"\s*,\s*collection\(db,\s*"branches",\s*(branch|b)\.id,\s*"months"\)\s*\]',
        lambda m: (
            '["months", page === "imports" ? collection(db,"branches",'
            + m[1] + '.id,"months") : query(collection(db,"branches",'
            + m[1] + '.id,"months"),'
            'where(documentId(),">=",`${Number(month.slice(0,4))-1}-01`),'
            'where(documentId(),"<",`${Number(month.slice(0,4))+1}-01`))]'
        ),
    )

    s = replace(
        s,
        '    month,\n  ]);',
        '    month,\n'
        '    page === "units" && branchId === "all" ? loadAllUnits : false,\n'
        '  ]);',
    )

    s = replace(s, 'setPage(id);', 'setLoadAllUnits(false);setPage(id);')

    s = sub(
        s,
        r'onChange=\{\((event|e)\) =>\s*setBranchId\(\1.target.value\)\s*\}',
        lambda m: (
            'onChange={(' + m[1]
            + ')=>{setLoadAllUnits(false);setBranchId('
            + m[1] + '.target.value);}}'
        ),
    )

    s = replace(
        s,
        '<OperationsInsights units={units} events={events} />',
        '<LightInsights branches={visible} events={events} month={month} />',
    )

    s = replace(
        s,
        '<RentalDetails type={modal.type} month={modal.month} total={modal.total} events={events} units={units} />',
        '<LazyUnits events={events.filter(e=>e.type===modal.type&&e.month===modal.month)} units={units}>{loaded=><RentalDetails type={modal.type} month={modal.month} total={modal.total} events={events} units={loaded} />}</LazyUnits>',
    )

    s = replace(
        s,
        '<ActivityUsage activity={modal.activity} month={modal.month} events={events} units={units} />',
        '<LazyUnits events={events.filter(e=>e.activities?.some((a:Row)=>a.id===modal.activity.id))} units={units}>{loaded=><ActivityUsage activity={modal.activity} month={modal.month} events={events} units={loaded} />}</LazyUnits>',
    )

    start = s.index('{page === "units" && (')
    at = s.index('<>', start) + 2
    s = s[:at] + '''
      {branchId === "all" &&
       branches.filter(b=>!b.archived).length > 1 &&
       !loadAllUnits && (
        <section className="panel target-panel">
          <p>請在右上角選擇據點，即可查看倉位。需要跨據點查看時，可載入全部倉位。</p>
          <button className="secondary" onClick={()=>setLoadAllUnits(true)}>
            載入全部倉位
          </button>
        </section>
      )}
    ''' + s[at:]

files["src/main.tsx"] = s

s = read("src/GoalsOverview.tsx")
if "where(documentId(),'>=',year)" not in s:
    s = imports(s, ['doc', 'documentId', 'getDoc', 'query', 'where'])

    s = replace(
        s,
        "const s=await getDocs(collection(db,'branches',b.id,'targets'));const g=s.docs.find(d=>d.id===p)?.data();",
        "const s=await getDoc(doc(db,'branches',b.id,'targets',p));const g=s.data();",
    )
    s = replace(
        s,
        "onSnapshot(collection(db,'branches',b.id,c),",
        "onSnapshot(query(collection(db,'branches',b.id,c),where(documentId(),'>=',year),where(documentId(),'<',String(Number(year)+1))),",
    )
    s = replace(
        s,
        "[Boolean(supplied),branches.map(b=>b.id).join(',')]",
        "[Boolean(supplied),branches.map(b=>b.id).join(','),year]",
    )

files["src/GoalsOverview.tsx"] = s

s = read("src/Targets.tsx")
if "where(documentId(),'>=',year)" not in s:
    s = imports(s, ['documentId', 'getDocs', 'query', 'where'])

    s = replace(
        s,
        "['targets','referrals','targetHistory','actuals']",
        "['targets','referrals','actuals']",
    )
    s = replace(
        s,
        "onSnapshot(collection(db,'branches',b.id,c),",
        "onSnapshot(query(collection(db,'branches',b.id,c),where(documentId(),'>=',year),where(documentId(),'<',String(Number(year)+1))),",
    )
    s = replace(
        s,
        "[branches.map(b=>b.id).join(',')]",
        "[branches.map(b=>b.id).join(','),year]",
    )
    s = replace(
        s,
        "onClick={()=>setHistory({branch:b,items:r.targetHistory||[]})}",
        '''onClick={async()=>{
          try {
            const s=await getDocs(collection(db,'branches',b.id,'targetHistory'));
            setHistory({
              branch:b,
              items:s.docs.map(d=>({id:d.id,...d.data()}))
            });
          } catch(e) {
            setError(e instanceof Error?e.message:String(e));
          }
        }}''',
    )

files["src/Targets.tsx"] = s

if (root / "src/annual-export.ts").exists():
    s = read("src/annual-export.ts")
    if "where(documentId(),'>=',year+'-01')" not in s:
        s = imports(s, ['documentId', 'query', 'where'])
        s = replace(
            s,
            "getDocs(collection(db,'branches',b.id,c))",
            "getDocs(query(collection(db,'branches',b.id,c),where(documentId(),'>=',year+'-01'),where(documentId(),'<',`${Number(year)+1}-01`)))",
        )
    files["src/annual-export.ts"] = s

for name, content in files.items():
    (root / name).write_text(content, encoding="utf-8")
    print("已更新 " + name)
