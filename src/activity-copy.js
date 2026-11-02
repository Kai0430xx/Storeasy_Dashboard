// activity-copy-v1: copy descriptive fields only.
export function activityCopyDraft(activity){
 const match=String(activity.month||'').match(
  /^(\d{4})-(0[1-9]|1[0-2])$/
 );
 if(!match)throw new Error('來源活動月份不合法，請重新整理');

 const year=Number(match[1]),month=Number(match[2]);
 const next=month===12
  ?`${year+1}-01`
  :`${year}-${String(month+1).padStart(2,'0')}`;

 return {
  kind:'activity',
  copy:true,
  branchId:activity.branchId,
  month:next,
  name:activity.name||'',
  description:activity.description||'',
  category:activity.category||''
 };
}
