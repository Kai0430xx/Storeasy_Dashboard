from pathlib import Path
import base64, gzip, re

root = Path(__file__).resolve().parents[1]
files = {}

def read(name):
    return (root / name).read_text(encoding="utf-8")

payload = """
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
"""

files["src/GoalsOverview.tsx"] = gzip.decompress(
    base64.b64decode(payload)
).decode("utf-8")

s = read("src/main.tsx")

if 'import GoalsOverview from "./GoalsOverview";' not in s:
    s = 'import GoalsOverview from "./GoalsOverview";\n' + s

if 'branches={visible} data={data} month={month}' not in s:
    start = s.index(
        '{page === "dashboard" && <>',
        s.index('營運目標與轉介') - 150,
    )
    end = s.index('{page === "targets" &&', start)
    s = s[:start] + '''{page === "dashboard" && <>
                <GoalsOverview
                  branches={visible} data={data} month={month}
                  global={Boolean(global)}
                />
                <OperationsInsights units={units} events={events} />
              </>}
              ''' + s[end:]

files["src/main.tsx"] = s

s = read("src/Targets.tsx")

conditions = {
    '出租率': 'monthly?.occupancy!=null',
    '業績完成率': 'monthly?.performance!=null',
    '轉介數量': 'monthly?.referrals!=null||ref?.count>0',
    '業績完成率（全年平均）': 'annual?.performance!=null',
    '出租率（12 月達標）': 'annual?.occupancy!=null',
    '轉介數量（全年加總）': 'annual?.referrals!=null||progress.referred>0',
}

if 'monthly?.occupancy!=null)&&' not in s:
    for label, condition in conditions.items():
        s, count = re.subn(
            r'<tr><td>' + re.escape(label) + r'</td>.*?</tr>',
            lambda m: '{(' + condition + ')&&' + m.group(0) + '}',
            s,
            count=1,
        )
        if count != 1:
            raise RuntimeError('找不到指標列：' + label)

s = s.replace(
    'className="badge yellow">超過 3 間・年終加成',
    'className="referral-bonus">超過 3 筆・年終加成',
)
files["src/Targets.tsx"] = s

s = read("src/style.css")
if '.referral-bonus' not in s:
    s += '''
.referral-bonus {
  display: block;
  color: #b91c1c;
  font-weight: 700;
}
'''
files["src/style.css"] = s

for name, content in files.items():
    (root / name).write_text(content, encoding="utf-8")
    print("已更新 " + name)
