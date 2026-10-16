import type {ReactNode} from 'react';
import './goal-disclosure.css';

export default function GoalDisclosure({
 collapsed,title,children
}: {
 collapsed:boolean;
 title:string;
 children:ReactNode;
}) {
 if(!collapsed)return <>{children}</>;

 return (
  <details className="goal-disclosure">
   <summary>{title}</summary>
   <div className="goal-disclosure-content">
    {children}
   </div>
  </details>
 );
}
