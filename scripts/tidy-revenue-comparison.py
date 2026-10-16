from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
main = root / 'src/main.tsx'
component = root / 'src/RevenueComparison.tsx'

source = main.read_text(encoding='utf-8')
content = component.read_text(encoding='utf-8')

pattern = r'<RevenueComparison\b[^>]*?/>'
if len(re.findall(pattern, source)) != 1:
    raise SystemExit('業績比較位置不唯一，未修改檔案')

source = re.sub(pattern, '', source)

anchor = re.search(
    r'<section className="panel">\s*<div className="panel-heading">'
    r'\s*<div>\s*<h2>活動使用概況</h2>',
    source,
)
if not anchor or '各據點營運概況' not in source[:anchor.start()]:
    raise SystemExit('找不到各據點營運概況後方位置，未修改檔案')

source = source[:anchor.start()] + (
    '<RevenueComparison key={branchId} branches={visible} data={data} '
    'month={month} collapsible={branchId === "all"}/>\n                  '
) + source[anchor.start():]

if 'function RevenueComparisonContent(' not in content:
    old = 'export default function RevenueComparison('
    if content.count(old) != 1:
        raise SystemExit('找不到業績比較元件，未修改檔案')

    content = content.replace(
        old,
        'function RevenueComparisonContent(',
        1,
    )
    content = 'import "./revenue-disclosure.css";\n' + content
    content += '''

type RevenueProps = {
  branches: Row[];
  data: Record<string, Row>;
  month: string;
  collapsible?: boolean;
};

export default function RevenueComparison({
  collapsible = false,
  ...props
}: RevenueProps) {
  if (!collapsible) {
    return <RevenueComparisonContent {...props}/>;
  }

  return (
    <details className="panel revenue-disclosure">
      <summary>業績去年同月比較</summary>
      <div className="revenue-disclosure-body">
        <p>
          {props.month} 與 {Number(props.month.slice(0, 4)) - 1}
          {props.month.slice(4)} · KPI 實際業績金額
        </p>
        <RevenueComparisonContent {...props}/>
      </div>
    </details>
  );
}
'''

css = '''
.revenue-disclosure {
  padding: 0;
}
.revenue-disclosure > summary {
  padding: 18px 22px;
  cursor: pointer;
  font-weight: 600;
}
.revenue-disclosure > summary:focus-visible {
  outline: 2px solid #204b80;
  outline-offset: -4px;
  border-radius: 10px;
}
.revenue-disclosure-body {
  padding: 0 22px 20px;
}
.revenue-disclosure-body > p {
  margin: 0 0 16px;
}
.revenue-disclosure-body > .panel {
  padding: 0;
  margin: 0;
  border: 0;
  box-shadow: none;
}
.revenue-disclosure-body .panel-heading {
  display: none;
}
'''

for path, text in [(main, source), (component, content)]:
    backup = path.with_name(path.name + '.before-revenue-layout')
    if not backup.exists():
        backup.write_text(
            path.read_text(encoding='utf-8'),
            encoding='utf-8',
        )
    path.write_text(text, encoding='utf-8')

(root / 'src/revenue-disclosure.css').write_text(
    css,
    encoding='utf-8',
)
print('已調整位置：全部據點預設收合，單一據點直接顯示')
