import {useRef,type InputHTMLAttributes} from 'react';

type Props=InputHTMLAttributes<HTMLInputElement>&{
 onClear:()=>void
};

export default function SearchInput({onClear,...props}:Props){
 const input=useRef<HTMLInputElement>(null);
 const label=props['aria-label']||props.placeholder||'搜尋';

 return <div className="clearable-search">
  <input
   {...props}
   ref={input}
   type="search"
   aria-label={label}
  />
  <button
   type="button"
   className="search-clear"
   aria-label={`清除${label}`}
   title="清除搜尋"
   disabled={props.disabled||!String(props.value??'')}
   onClick={()=>{
    onClear();
    input.current?.focus();
   }}
  >×</button>
 </div>;
}
