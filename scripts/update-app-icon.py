from pathlib import Path
import json, re, struct, hashlib

root = Path(__file__).resolve().parents[1]
image = root / 'public/icons/storeasy-icon.png'

if not image.exists():
    raise SystemExit('請先上傳 public/icons/storeasy-icon.png')

data = image.read_bytes()
if data[:8] != b'\x89PNG\r\n\x1a\n' or len(data) < 24:
    raise SystemExit('請上傳真正的 PNG 圖片，不能只改副檔名。')

w, h = struct.unpack('!II', data[16:24])
if w != h or w < 512:
    raise SystemExit('請使用至少 512×512 的正方形 PNG。')

version = hashlib.sha256(data).hexdigest()[:12]
url = 'icons/storeasy-icon.png?v=' + version

path = root / 'public/manifest.webmanifest'
manifest = json.loads(path.read_text(encoding='utf-8'))
manifest['name'] = '收多易營運管理平台'
manifest['short_name'] = '收多易'
manifest['icons'] = [{
    'src': url,
    'sizes': f'{w}x{h}',
    'type': 'image/png',
    'purpose': 'any'
}]
path.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
    encoding='utf-8'
)

path = root / 'index.html'
html = path.read_text(encoding='utf-8')
html = re.sub(
    r'<link\b[^>]*\brel=["\']apple-touch-icon["\'][^>]*>',
    '',
    html
)
html = html.replace(
    '</head>',
    f'<link rel="apple-touch-icon" href="./{url}"/></head>'
)
path.write_text(html, encoding='utf-8')

worker = root / 'public/sw.js'
if worker.exists():
    text = worker.read_text(encoding='utf-8')
    text = re.sub(
        r'icons/(?:app-192|storeasy-icon)\.png'
        r'(?:\?v=[a-zA-Z0-9_-]+)?',
        url,
        text
    )
    worker.write_text(text, encoding='utf-8')

manual = root / 'src/manual-content.ts'
text = manual.read_text(encoding='utf-8')
if '// custom-app-icon-manual-v1' not in text:
    text += '''
// custom-app-icon-manual-v1
(manualPages.find(p=>p.id==='notifications')||
 manualPages.find(p=>p.id==='users'))?.topics.push({
 title:'更新手機桌面圖示',
 steps:[
  '網站更新後，手機加入主畫面會使用自訂的收多易圖示。',
  '舊圖示若未更新，請移除舊捷徑，再用 Safari 分享 → 加入主畫面；重新登入並核對通知設定，必要時重新啟用。'
 ],
 result:'更換圖示不會刪除帳號或雲端營運資料；圖示更新時間依手機系統快取而定。'
});
'''
    manual.write_text(text, encoding='utf-8')

print('已設定自訂桌面圖示、通知圖示及操作手冊。')
