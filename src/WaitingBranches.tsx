
import {useState} from 'react';

export default function WaitingBranches({labels}:{labels:string[]}){
 const [expanded,setExpanded]=useState(false);
 return <span className="waiting-branch-summary">
  {(expanded?labels:labels.slice(0,3)).join('、')}
  {labels.length>3&&
   <button type="button" className="text-button"
    aria-label={expanded?'收合候補據點':'展開全部候補據點'}
    onClick={()=>setExpanded(v=>!v)}>
    {expanded?'收合':'…'}
   </button>
  }
 </span>;
}
