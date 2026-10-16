from pathlib import Path

root = Path(__file__).resolve().parents[1]
main = root / 'src/main.tsx'
source = main.read_text(encoding='utf-8')

if 'import BranchOverviewDisclosure' not in source:
    title = source.find('<h2>各據點營運概況</h2>')
    if title < 0:
        raise SystemExit('找不到各據點營運概況，未修改檔案')

    start = source.rfind('<section className="panel">', 0, title)
    end = source.find('</section>', title)
    if start < 0 or end < 0:
        raise SystemExit('找不到完整概況區塊，未修改檔案')

    end += len('</section>')
    source = (
        source[:start]
        + '<BranchOverviewDisclosure key={branchId} '
        + 'collapsed={branchId === "all"}>'
        + source[start:end]
        + '</BranchOverviewDisclosure>'
        + source[end:]
    )
    source = (
        'import BranchOverviewDisclosure '
        'from "./BranchOverviewDisclosure";\n'
        + source
    )

component = '''import type {ReactNode} from 'react';
import './branch-overview-disclosure.css';

export default function BranchOverviewDisclosure({
  collapsed,
  children,
}: {
  collapsed: boolean;
  children: ReactNode;
}) {
  if (!collapsed) return <>{children}</>;

  return (
    <details className="panel branch-overview-disclosure">
      <summary>各據點營運概況</summary>
      <div className="branch-overview-disclosure-body">
        {children}
      </div>
    </details>
  );
}
'''

css = '''
.branch-overview-disclosure {
  padding: 0;
}
.branch-overview-disclosure > summary {
  padding: 18px 22px;
  cursor: pointer;
  font-weight: 600;
}
.branch-overview-disclosure > summary:focus-visible {
  outline: 2px solid #204b80;
  outline-offset: -4px;
  border-radius: 10px;
}
.branch-overview-disclosure-body {
  padding: 0 22px 20px;
}
.branch-overview-disclosure-body > .panel {
  padding: 0;
  margin: 0;
  border: 0;
  box-shadow: none;
}
.branch-overview-disclosure-body .panel-heading h2 {
  display: none;
}
'''

backup = main.with_name('main.tsx.before-branch-overview-collapse')
if not backup.exists():
    backup.write_text(
        main.read_text(encoding='utf-8'),
        encoding='utf-8',
    )

main.write_text(source, encoding='utf-8')
(root / 'src/BranchOverviewDisclosure.tsx').write_text(
    component,
    encoding='utf-8',
)
(root / 'src/branch-overview-disclosure.css').write_text(
    css,
    encoding='utf-8',
)

print('各據點營運概況：全部據點預設收合，單一據點直接顯示')
