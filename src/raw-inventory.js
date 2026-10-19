
import {parseUnits} from './imports.js';
const norm=v=>String(v??'').normalize('NFKC').trim();
const missing=v=>v==null||typeof v==='number'&&!Number.isFinite(v)||/^(?:|[+-]?(?:∞|infinity)|nan|n\/?a|無數值|无数值|無|无|#(?:DIV\/0!|VALUE!|N\/A|NUM!|REF!|NAME\?|NULL!)|[-—–])$/i.test(norm(v));

function cleanNumber(v,cell,fixes){
 if(missing(v)){
  if(v!==0)fixes.push({cell,before:String(v??'空白'),after:0});
  return 0;
 }
 const text=norm(v).replace(/NT\$|NTD|TWD|元|[$,\s]/gi,'');
 const n=Number(text);
 if(!text||!Number.isFinite(n)||n<0)throw Error(cell+' 數值不合法，請檢查原檔');
 return n;
}

function cleanDimensions(value,cell,fixes){
 const text=norm(value),num='\\d+(?:\\.\\d+)?';
 const part=`${num}\\s*[*xX×]\\s*${num}\\s*[*xX×]\\s*${num}`;
 const match=text.match(new RegExp(`^(${part}(?:\\s*[+-]\\s*${part})*)`));
 if(!match)throw Error(cell+' 尺寸格式無法辨識');
 const rest=text.slice(match[0].length).trim();
 if(rest&&!rest.split(/\s+/).every(v=>/^\d+(?:\.\d+)?$/.test(v))){
  throw Error(cell+' 尺寸後有無法辨識的文字');
 }
 if(rest)fixes.push({cell,before:text,after:match[1].trim()});
 return match[1].trim();
}

// raw-inventory-simple-v2
export function parseInventoryFile(book){
 const name=book.SheetNames[0],raw=book.Sheets[name];
 if(!raw?.length)throw Error('工作表沒有資料');
 const fixes=[];

 if(raw[0].some(v=>['倉位','倉位編號','倉號'].includes(norm(v)))){
  const headers=raw[0].map(v=>norm(v).replace(/\s/g,'').replace(/\((?:NT\$|NTD|元|新臺幣|新台幣)\)/gi,''));
  const numeric=['材積','材積數','單價','月租','月租金','月租金額','原價','月繳','金額'];
  const rows=raw.map((r,i)=>i===0?r:Array.from(
   {length:Math.max(raw[0].length,r.length)},
   (_,c)=>numeric.includes(headers[c])
    ?cleanNumber(r[c],`第 ${i+1} 列 ${headers[c]}`,fixes)
    :r[c]
  ));
  return {
   units:parseUnits({...book,Sheets:{...book.Sheets,[name]:rows}},name,{requirePrice:true,requireLease:true}),
   report:{format:'有標題倉位表',merged:0,fixes}
  };
 }

 const ignored=new Map();
 for(const range of book.Merges?.[name]||[]){
  const m=range.match(/^\$?B\$?(\d+):\$?B\$?(\d+)$/);
  if(m)for(let r=Number(m[1])+1;r<=Number(m[2]);r++)ignored.set(r,Number(m[1]));
 }

 const rows=[['倉位','尺寸','材積','單價','月租','租期']];
 let merged=0;
 for(let i=0;i<raw.length;i++){
  const r=raw[i];
  if(!r.some(v=>norm(v)))continue;
  if(norm(r[0])||!norm(r[1])||!norm(r[2])||r.slice(13).some(v=>norm(v))){
   throw Error(`第 ${i+1} 列不是支援的原始格式，請確認欄位`);
  }
  if(ignored.has(i+1)){
   const master=raw[ignored.get(i+1)-1];
   if([1,2,3,5,6,10].some(c=>norm(r[c])!==norm(master[c]))){
    throw Error(`第 ${i+1} 列合併倉位有不同資料`);
   }
   merged++;
   continue;
  }
  const code=norm(r[1]);
  if(!/\d/.test(code))throw Error(`第 ${i+1} 列倉號無法辨識`);
  rows.push([
   code,
   cleanDimensions(r[2],`C${i+1} (${code})`,fixes),
   cleanNumber(r[3],`D${i+1} (${code})`,fixes),
   cleanNumber(r[5],`F${i+1} (${code})`,fixes),
   cleanNumber(r[6],`G${i+1} (${code})`,fixes),
   r[10]
  ]);
 }
 return {
  units:parseUnits({SheetNames:[name],Sheets:{[name]:rows}},name,{requirePrice:true,requireLease:true}),
  report:{
   format:'系統原始下載檔',merged,fixes,
   ignored:'略過 A 欄、坪數 E 欄、季／半年／年繳 H～J 欄及租期後 L／M 欄；備註不影響倉位數與空倉判斷。'
  }
 };
}
