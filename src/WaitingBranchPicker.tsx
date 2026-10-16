type Branch = Record<string, any>;

export default function WaitingBranchPicker({
 branches,ownedIds,global,selected,onChange,
 other,onOtherChange,otherName,onOtherNameChange
}: {
 branches: Branch[];
 ownedIds: string[];
 global: boolean;
 selected: string[];
 onChange: (ids: string[])=>void;
 other: boolean;
 onOtherChange: (value: boolean)=>void;
 otherName: string;
 onOtherNameChange: (value: string)=>void;
}) {
 const mine=branches.filter(b=>ownedIds.includes(b.id));
 const rest=branches.filter(b=>!ownedIds.includes(b.id));
 const checkedRest=rest.filter(b=>selected.includes(b.id)).length;

 const options=(rows:Branch[]) => (
  <div className="waiting-branch-grid">
   {rows.map(b=>
    <label key={b.id}>
     <input
      type="checkbox"
      checked={selected.includes(b.id)}
      onChange={e=>onChange(
       e.target.checked
        ?[...selected,b.id]
        :selected.filter(id=>id!==b.id)
      )}
     />
     <span>{b.name}</span>
    </label>
   )}
  </div>
 );

 return (
  <fieldset className="waiting-branches">
   <legend>候補據點（可複選）</legend>

   {mine.length>0 && <>
    <p className="waiting-branch-group-title">所屬據點</p>
    {options(mine)}
   </>}

   {!mine.length && !global &&
    <p className="hint">
     目前沒有指派的所屬據點，可展開其它系統據點選擇。
    </p>
   }

   {rest.length>0 &&
    <details className="waiting-other-branches">
     <summary>
      其它系統據點
      <span>已選 {checkedRest}／{rest.length}</span>
     </summary>
     {options(rest)}
    </details>
   }

   <div className="waiting-branch-grid waiting-custom-branch">
    <label>
     <input
      type="checkbox"
      checked={other}
      onChange={e=>onOtherChange(e.target.checked)}
     />
     <span>其它據點</span>
    </label>
   </div>

   <p className="hint">
    候補不在系統內的據點時，勾選「其它據點」並自行填寫名稱。
   </p>

   {other &&
    <label>
     其它據點名稱
     <input
      required
      maxLength={300}
      placeholder="多個據點可用頓號分隔"
      value={otherName}
      onChange={e=>onOtherNameChange(e.target.value)}
     />
    </label>
   }
  </fieldset>
 );
}
