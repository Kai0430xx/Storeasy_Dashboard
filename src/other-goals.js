export const otherKeys = Array.from({length:10}, (_,i)=>`o${i}`);
export function normalizeOtherGoals(other = {}) {
  if (!other || typeof other !== 'object' || Array.isArray(other) || Object.keys(other).some(k=>!otherKeys.includes(k))) throw Error('其它目標最多 10 項');
  return Object.fromEntries(Object.entries(other).map(([key,g])=>{
    const name=String(g.name||'').trim(), id=String(g.id||'');
    const target=g.target===''||g.target==null?NaN:Number(g.target);
    if (!name || name.length>80 || !/^[a-zA-Z0-9_-]{1,80}$/.test(id) || !Number.isFinite(target) || target<0 || target>1e9) throw Error('其它目標請填名稱及非負目標數量');
    return [key,{id,name,target}];
  }));
}
export function normalizeOtherActuals(goals = {}, values = {}) {
  return Object.fromEntries(Object.entries(goals).filter(([key,g])=>values[key]?.goalId===g.id && values[key].value!=='' && values[key].value!=null).map(([key,g])=>{
    const value=Number(values[key].value);
    if (!Number.isFinite(value) || value<0 || value>1e9) throw Error('其它目標實際數量須為非負數');
    return [key,{goalId:g.id,value}];
  }));
}
export function otherProgress(goals = {}, actuals = {}, future = false) {
  return Object.entries(goals).map(([key,g])=>{
    const saved=actuals[key], actual=saved?.goalId===g.id && typeof saved.value==='number'?saved.value:null;
    return {key,...g,actual,result:future?'尚未到月份':actual==null?'待填寫':actual>=g.target?'達標':'未達標'};
  });
}
