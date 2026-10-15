from pathlib import Path
import re

helper = r'''
// storeasy-inventory-signature-v2
function canonicalInventoryValue(value){
 if(Array.isArray(value))return value.map(canonicalInventoryValue);
 if(value!==null&&typeof value==='object')return Object.fromEntries(
  Object.keys(value).sort().map(key=>[key,canonicalInventoryValue(value[key])])
 );
 return value;
}
function stableInventoryJSON(value){
 return JSON.stringify(canonicalInventoryValue(value));
}
export function sameInventorySignature(row,signature){
 if(!row)return signature===null;
 if(typeof signature!=='string')return false;
 try{
  return inventorySignature(row)===stableInventoryJSON(JSON.parse(signature));
 }catch{return false;}
}
'''

paths = [
    Path('src/inventory-diff.js'),
    Path('src/review-inventory.ts')
]
texts = {p: p.read_text(encoding='utf-8') for p in paths}
model = texts[paths[0]]
service = texts[paths[1]]

if '// storeasy-inventory-signature-v2' in model:
    print('此修正已套用，不需重複執行。')
    raise SystemExit(0)

pattern = (
    r'(export\s+function\s+inventorySignature\s*\(row\)'
    r'\s*\{[\s\S]*?return\s+)JSON\.stringify\('
)
model, count = re.subn(
    pattern,
    r'\g<1>stableInventoryJSON(',
    model,
    count=1
)
if count != 1:
    raise SystemExit('找不到倉位比對函式，未修改任何檔案。')

model += '\n' + helper

service, imports = re.subn(
    r'(import\s*\{\s*)inventorySignature\s*,',
    r'\g<1>sameInventorySignature,inventorySignature,',
    service,
    count=1
)

service, previews = re.subn(
    r'inventorySignature\(old\)\s*!==\s*job\.signature',
    '!sameInventorySignature(old,job.signature)',
    service
)

service, retries = re.subn(
    r'inventorySignature\(old\)\s*===\s*old\.reviewImport\.after',
    'sameInventorySignature(old,old.reviewImport.after)',
    service
)

if (imports, previews, retries) != (1, 2, 1):
    raise SystemExit(
        f'匯入程式版本不符：{imports}/{previews}/{retries}，'
        '未修改任何檔案。'
    )

texts[paths[0]] = model
texts[paths[1]] = service

for path, content in texts.items():
    backup = path.with_name(path.name + '.before-signature-fix')
    if not backup.exists():
        backup.write_text(
            path.read_text(encoding='utf-8'),
            encoding='utf-8'
        )
    path.write_text(content, encoding='utf-8')

print('已修正差異比對誤判；保留真正資料變更的衝突檢查。')
