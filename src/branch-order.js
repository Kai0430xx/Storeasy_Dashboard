
// 只排序既有據點，不建立或改名。
export const branchOrder = [
 '永和','中和好市多','中和二號','中和立德',
 '威力','環球','板橋','湯城','光復',
 '新店','新店民族','淡水','海洋都心',
 '新莊昌隆','新莊公園','土城','新竹',
 '台中英士','台中中港','台中青海','台中文心',
 '台中豐原','台中漢口','台中豐原成功',
 '台南安平','台南民生',
 '高雄博愛','高雄九如','高雄復興','高雄左營','高雄苓雅',
];

const aliases = {
 '中和好市多':['中一'],
 '中和二號':['中二'],
 '中和立德':['中三'],
 '海洋都心':['淡水海都','海都'],
};

const clean = name => String(name || '')
 .normalize('NFKC')
 .replace(/臺/g,'台')
 .replace(/[\s・·_-]/g,'')
 .replace(/^收多易/,'')
 .replace(/(?:迷你倉庫|迷你倉|據點|店)$/,'');

const groups = [
 '永和','板橋','湯城','光復','新店','淡水','土城','新竹'
];

const labels = branchOrder.flatMap((label,index)=>
 [label,...(aliases[label]||[])].map(value=>({
   label:clean(value),index
 }))
).sort((a,b)=>b.label.length-a.label.length);

export function branchRank(name) {
 const n=clean(name);
 const matched=labels.find(v=>
   n===v.label ||
   n.endsWith(v.label) ||
   (groups.includes(v.label)&&n.startsWith(v.label))
 );
 return matched?.index ?? branchOrder.length;
}

export function compareBranches(a,b) {
 return branchRank(a.name)-branchRank(b.name)
   || String(a.name||'').localeCompare(
     String(b.name||''),
     'zh-Hant-u-co-stroke',
     {numeric:true}
   )
   || String(a.id||'').localeCompare(String(b.id||''));
}
