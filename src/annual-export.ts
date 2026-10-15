import {operatingMonths} from './operating-months.js';
import {otherProgress} from './other-goals.js';
import { effectiveMonths } from "./actuals.js";
import { collection, doc, getDoc, getDocs, documentId, query, where } from "firebase/firestore";
import {auth,db} from './firebase';
import {compareBranches} from './branch-order.js';
import {taipeiDate} from './domain.js';
type Row=Record<string,any>;
export function annualExportRows(branches:Row[],records:Row,year:string,today:string){
 if(!/^20\d{2}$/.test(year))throw new Error('年度不合法');
 const output:Row[]=[];
 const check=(target:any,actual:any,future:boolean,missing:string)=>target==null?'未設定':future?'尚未到月份':actual==null?missing:actual>=target?'達標':'未達標';
 for(const b of [...branches].sort(compareBranches))for(let i=1;i<=12;i++){
  const notOpen=i<operatingMonths(year,b).startMonth;
  const month=`${year}-${String(i).padStart(2,'0')}`,r=records[b.id]||{},goal=r.targets?.find((v:Row)=>v.id===month),kpi=effectiveMonths(r.months||[],r.actuals||[]).find((v:Row)=>(v.id||v.month)===month&&v.source==='import'),ref=r.referrals?.find((v:Row)=>(v.id||v.month)===month),future=month>today.slice(0,7);
  const occupancy=kpi?.kpiMetrics?.occupancy??(kpi?.total>0&&typeof kpi.rented==='number'?kpi.rented/kpi.total*100:null),performance=kpi?.kpiMetrics?.performance??null;
  const statuses=[check(goal?.occupancy,occupancy,future,'待匯入 KPI'),check(goal?.performance,performance,future,'待匯入 KPI'),check(goal?.referrals,ref?.count,future,'轉介未填')];
  const other=otherProgress(goal?.other||{},r.actuals?.find((a:Row)=>(a.id||a.month)===month)?.other||{},future);
  if(notOpen){statuses.fill('未開幕');for(const g of other)g.result='未開幕';}
  const required=[...statuses,...other.map((v:Row)=>v.result)].filter(s=>s!=='未設定');
  const overall=notOpen?'未開幕':!required.length?'未設定':future?'尚未到月份':required.some(s=>s==='待匯入 KPI'||s==='轉介未填'||s==='待填寫')?'資料未齊':required.every(s=>s==='達標')?'達標':'未達標';
  output.push({notOpen,other,branchId:b.id,name:b.name,month,occupancyTarget:goal?.occupancy??null,occupancy,occupancyResult:statuses[0],performanceTarget:goal?.performance??null,performance,performanceResult:statuses[1],referralTarget:goal?.referrals??null,referrals:ref?.count??null,referralResult:statuses[2],overall,bonus:ref?.count>3?'超過 3 筆・年終加成':'',kpiFile:(kpi?.sourceFile||'未匯入')+(kpi?.manualActuals?'（手動修正：'+(r.actuals?.find((a:Row)=>(a.id||a.month)===month)?.reason||'')+'）':'')});
 }
 return output;
}
export async function createAnnualWorkbook(branches:Row[],records:Row,year:string,today:string){
 const ExcelJS=(await import('exceljs')).default;
 const book=new ExcelJS.Workbook();book.creator='收多易迷你倉庫';
 const rows=annualExportRows(branches,records,year,today);
 const summary=book.addWorksheet('全據點年度總表');
 const headers=['據點'];for(let i=1;i<=12;i++)headers.push(`${i}月達標結果`,`${i}月轉介數量`);
 summary.addRow(headers);
 for(const b of [...branches].sort(compareBranches)){
  const values:any[]=[b.name];const selected=rows.filter(r=>r.branchId===b.id);for(const r of selected)values.push(r.overall,r.referrals??'');const row=summary.addRow(values);
  selected.forEach((r,i)=>{if(r.bonus){const cell=row.getCell(i*2+3);cell.font={bold:true,color:{argb:'FFB91C1C'}};cell.note=r.bonus;}});
 }
 const details=book.addWorksheet('每月目標明細');
 details.columns=[{header:'據點',key:'name',width:20},{header:'月份',key:'month',width:13},{header:'出租率目標',key:'occupancyTarget',width:16},{header:'實際出租率',key:'occupancy',width:16},{header:'出租率結果',key:'occupancyResult',width:18},{header:'業績完成率目標',key:'performanceTarget',width:20},{header:'實際業績完成率',key:'performance',width:20},{header:'業績結果',key:'performanceResult',width:18},{header:'轉介目標',key:'referralTarget',width:14},{header:'轉介數量',key:'referrals',width:14},{header:'轉介結果',key:'referralResult',width:18},{header:'整體月目標結果',key:'overall',width:20},{header:'轉介加成提示',key:'bonus',width:26},{header:'KPI 來源檔案',key:'kpiFile',width:40}];
 for(const r of rows){const value={...r};for(const key of ['occupancyTarget','occupancy','performanceTarget','performance'])value[key]=r[key]==null?'—':r[key]/100;value.referralTarget=r.referralTarget??'未設定';value.referrals=r.referrals??'';const row=details.addRow(value);if(r.bonus)for(const i of [10,13])row.getCell(i).font={bold:true,color:{argb:'FFB91C1C'}};}
 for(const column of [3,4,6,7])details.getColumn(column).numFmt='0.00%';
 summary.columns.forEach((c,i)=>{c.width=i===0?20:17;});
 const otherSheet=book.addWorksheet('其它目標明細');
 otherSheet.columns=[{header:'據點',key:'name',width:20},{header:'月份',key:'month',width:13},{header:'目標名稱',key:'goalName',width:30},{header:'目標數量',key:'target',width:16},{header:'實際數量',key:'actual',width:16},{header:'達標結果',key:'result',width:18}];
 for(const r of rows)for(const g of r.other)otherSheet.addRow({name:r.name,month:r.month,goalName:g.name,target:g.target,actual:g.actual??'未填',result:g.result});
 for(const sheet of [summary,details,otherSheet]){sheet.views=[{state:'frozen',xSplit:1,ySplit:1}];sheet.autoFilter={from:{row:1,column:1},to:{row:sheet.rowCount,column:sheet.columnCount}};sheet.getRow(1).height=28;sheet.getRow(1).eachCell(c=>{c.font={bold:true,color:{argb:'FFFFFFFF'}};c.fill={type:'pattern',pattern:'solid',fgColor:{argb:'FF193F72'}};});}
 const notes=book.addWorksheet('說明');notes.addRows([['報表年度',year],['匯出日期（台灣）',today],['範圍','所有有權限查看且未封存的據點，不受畫面單一據點篩選影響'],['達標規則','月目標有設定的各項指標全部達標，整體才列為達標；有缺值列為資料未齊。'],['資料來源','出租率與業績完成率使用匯入 KPI；轉介使用各月手填明細數量；其它目標使用店長手填實際數量，達到目標數量即達標。'],['缺值','未設定目標、未匯入 KPI、未填轉介與未到月份會分別標示，不當成 0。'],['轉介提示','當月超過 3 筆以紅字標示年終加成，未自行計算獎金。'],['年度目標','本報表比較每月目標，不以年度目標代替未設定的月目標。']]);notes.getColumn(1).width=24;notes.getColumn(2).width=100;
 for (const sheet of book.worksheets) {
  if (sheet.name === '說明') continue;
  sheet.eachRow((row, rowNumber) => {
   if (rowNumber === 1) return;
   row.eachCell(cell => {
    if (cell.value === '達標' || cell.value === '已達標') {
     cell.font = {...cell.font, bold:true, color:{argb:'FFB91C1C'}};
    }
   });
  });
 }
 return book;
}
export async function exportAnnualTargets(year:string){
 const uid=auth.currentUser?.uid;if(!uid)throw new Error('請先登入');const actor=(await getDoc(doc(db,'users',uid))).data();if(!actor||!['admin','supervisor','manager','employee'].includes(actor.role))throw new Error('尚未取得據點權限');
 let branches:Row[]=[];
 if(['admin','supervisor'].includes(actor.role)){const snapshot=await getDocs(collection(db,'branches'));branches=snapshot.docs.map(d=>({id:d.id,...d.data()}));}
 else {const snapshots=await Promise.all([...new Set<string>(actor.branchIds||[])].map(id=>getDoc(doc(db,'branches',id))));branches=snapshots.filter(s=>s.exists()).map(s=>({id:s.id,...s.data()}));}
 branches=branches.filter(b=>!b.archived);if(!branches.length)throw new Error('沒有可匯出的據點');
 const records:Row={};for(const b of branches){records[b.id]={};for(const c of ['targets','months','referrals','actuals']){const snapshot=await getDocs(query(collection(db,'branches',b.id,c),where(documentId(),'>=',year+'-01'),where(documentId(),'<',`${Number(year)+1}-01`)));records[b.id][c]=snapshot.docs.map(d=>({id:d.id,...d.data()}));}}
 const book=await createAnnualWorkbook(branches,records,year,taipeiDate());const buffer=await book.xlsx.writeBuffer();const blob=new Blob([buffer],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=`收多易_${year}_全據點月目標與轉介.xlsx`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);
}

// storeasy-other-monthly-v1

// storeasy-achieved-red-v1

// storeasy-opening-month-v1
