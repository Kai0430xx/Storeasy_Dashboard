from pathlib import Path
import re

main = Path('src/main.tsx')
style = Path('src/style.css')
text = main.read_text(encoding='utf-8')
css = style.read_text(encoding='utf-8')

if 'className="renewal-payment-option"' not in text:
    pattern = (
        r'<label className="check-label">\s*'
        r'<input type="checkbox" name="unpaid"\s*/>\s*'
        r'未付款<small className="hint">[\s\S]*?</small></label>'
    )
    replacement = '''<div className="renewal-payment-option">
 <label className="renewal-payment-toggle">
  <input type="checkbox" name="unpaid" aria-describedby="renewal-unpaid-help" />
  <span>未付款</span>
 </label>
 <p id="renewal-unpaid-help" className="renewal-payment-help">先更新租期並列入待收款，確認收款後才計入續約。</p>
</div>'''
    text, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise SystemExit('找不到未付款選項，尚未修改任何檔案。')

if '/* renewal-payment-layout-v1 */' not in css:
    css += '''
/* renewal-payment-layout-v1 */
.renewal-payment-option {
  margin: 14px 0;
  padding: 12px 14px;
  background: #f5f8fc;
  border: 1px solid #e0e8f2;
  border-radius: 10px;
}
.renewal-payment-option .renewal-payment-toggle {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  margin: 0;
  width: fit-content;
  cursor: pointer;
}
.renewal-payment-toggle input[type="checkbox"] {
  flex: 0 0 16px;
  width: 16px;
  height: 16px;
  margin: 0;
  padding: 0;
}
.renewal-payment-toggle span {
  flex: 0 0 auto;
  white-space: nowrap;
  line-height: 1.5;
}
.renewal-payment-option .renewal-payment-help {
  display: block;
  margin: 7px 0 0;
  color: #7b8ca7;
  font-size: 12px;
  line-height: 1.7;
  overflow-wrap: anywhere;
}
'''

changes = {str(main): text, str(style): css}

for name in ['src/main.tsx', 'src/WorkTasks.tsx']:
    source = changes.get(name, Path(name).read_text(encoding='utf-8'))
    pattern = (
        r'<input\s+([^<>]*?'
        r'(?:placeholder="搜尋|aria-label="搜尋)[\s\S]*?)/>'
    )

    def replace_search(match):
        attrs = match.group(1)
        setter = re.search(r'set(Search|Person|Query)\(', attrs, re.I)
        if not setter:
            raise SystemExit(
                f'找不到搜尋狀態：{name}，未修改任何檔案。'
            )
        return (
            '<SearchInput ' + attrs
            + ' onClear={()=>'
            + setter.group(0)[:-1]
            + "('')}/>"
        )

    source, count = re.subn(pattern, replace_search, source)

    if count == 0 and 'SearchInput' not in source:
        raise SystemExit(f'找不到搜尋欄：{name}，未修改任何檔案。')

    if 'import SearchInput from' not in source:
        source = 'import SearchInput from "./SearchInput";\n' + source

    changes[name] = source

changes['src/SearchInput.tsx'] = r'''
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
'''.lstrip()

if '/* clearable-search-v1 */' not in changes[str(style)]:
    changes[str(style)] += '''
/* clearable-search-v1 */
.clearable-search {
  position: relative;
  min-width: 0;
  width: 100%;
  max-width: 245px;
}
.clearable-search input {
  display: block;
  width: 100%;
  box-sizing: border-box;
  padding-right: 38px;
}
.search .clearable-search {
  width: 245px;
}
.clearable-search input::-webkit-search-cancel-button,
.clearable-search input::-webkit-search-decoration {
  display: none;
  -webkit-appearance: none;
}
.clearable-search > .search-clear {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  margin: 0;
  padding: 0;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: #73849a;
  font-size: 21px;
  line-height: 1;
  box-shadow: none;
  cursor: pointer;
}
.clearable-search > .search-clear:hover:enabled {
  background: #edf2f8;
  color: #173f75;
}
.clearable-search > .search-clear:disabled {
  opacity: .35;
  cursor: default;
}
.clearable-search > .search-clear:focus-visible {
  outline: 2px solid #173f75;
  outline-offset: -2px;
}
.work-filters > .clearable-search {
  flex: 0 1 240px;
}
@media(max-width:720px) {
  .search .clearable-search {
    width: 100%;
    max-width: none;
    flex: 1;
  }
  .clearable-search {
    max-width: 100%;
  }
}
'''

for name, content in changes.items():
    path = Path(name)
    backup = path.with_name(path.name + '.before-ui-cleanup')
    if path.exists() and not backup.exists():
        backup.write_text(
            path.read_text(encoding='utf-8'),
            encoding='utf-8'
        )
    path.write_text(content, encoding='utf-8')

print('已整理未付款排版，並為所有搜尋欄加入清除按鈕。')
