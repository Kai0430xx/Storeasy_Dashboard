from pathlib import Path
import base64, gzip, json, re

root = Path(__file__).resolve().parents[1]
marker = 'storeasy-annual-renew-backfill-v2'

payload = (
    "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"
)

data = json.loads(gzip.decompress(base64.b64decode(payload)))
files = {}

for name, steps in data['ops'].items():
    s = (root / name).read_text(encoding='utf-8')
    if marker in s:
        continue

    for kind, old, new in steps:
        if kind == 'prepend':
            s = new + s
        elif kind == 'replace':
            if s.count(old) != 1:
                raise RuntimeError('版本不符，未寫入：' + name + '；' + old[:60])
            s = s.replace(old, new, 1)
        elif kind == 'regex':
            def replacement(match):
                value = new
                for i, group in enumerate(match.groups(), 1):
                    value = value.replace('@@' + str(i) + '@@', group or '')
                return value

            s, count = re.subn(old, replacement, s)
            if count != 1:
                raise RuntimeError('找不到唯一更新位置：' + name)
        else:
            raise RuntimeError('未知更新種類')

    files[name] = s + '\n// ' + marker + '\n'

for name, content in data['new'].items():
    p = root / name
    if (
        name not in data['overwrite']
        and p.exists()
        and p.read_text(encoding='utf-8') != content
    ):
        raise RuntimeError('請先核對現有檔案：' + name)
    files[name] = content

for name, content in files.items():
    (root / name).write_text(content, encoding='utf-8')
    print('已更新 ' + name)

print('完成：請發布更新後的 Firebase 規則；補舊分項請選「只補續約租期分項」。')
