import type {ReactNode} from 'react';
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
