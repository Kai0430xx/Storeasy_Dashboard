import type {ReactNode} from 'react';
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
