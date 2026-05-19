"""Deep-dive into sinoptik.htm form structure."""
import re

with open('sinoptik.htm', 'r', encoding='utf-8') as f:
    html = f.read()

# Extract 600 chars around each key element
def context(pattern, chars=400):
    for m in re.finditer(pattern, html):
        start = max(0, m.start() - chars//2)
        end = min(len(html), m.end() + chars//2)
        snippet = html[start:end]
        snippet = re.sub(r'\s+', ' ', snippet)
        print(f'\n  [{m.group()[:60]}]')
        print(f'  ...{snippet[:600]}...')
        print()

print('=== SELECT-STATION combobox structure ===')
context(r'id=select-station', 600)

print('\n=== SELECT-OBSERVER combobox structure ===')
context(r'id=select-observer', 400)

print('\n=== INPUT-JAM combobox structure ===')
context(r'id=input-jam[^-]', 400)

print('\n=== DATE PICKER structure ===')
context(r'input-datepicker__value_', 400)

print('\n=== ANT-SELECT full combobox div pattern ===')
combos = re.findall(r'<div[^>]*role=combobox[^>]*>[^<]{0,200}', html)
for c in combos[:8]:
    print(f'  {c[:300]}')

print('\n=== All aria-label values ===')
aria_labels = re.findall(r'aria-label=["\']([^"\']{1,80})["\']', html)
for al in sorted(set(aria_labels)):
    print(f'  {al}')

print('\n=== All placeholder values ===')
placeholders = re.findall(r'placeholder=["\']([^"\']{1,80})["\']', html)
for pl in sorted(set(placeholders)):
    print(f'  {pl}')

print('\n=== All visible label text content ===')
label_parts = re.findall(r'<label[^>]*>(.*?)</label>', html, re.DOTALL)
for lp in label_parts:
    clean = re.sub(r'<[^>]+>', '', lp).strip()
    clean = re.sub(r'\s+', ' ', clean)
    if 3 < len(clean) < 100:
        print(f'  {clean}')

print('\n=== Input elements ===')
inputs = re.findall(r'<input[^>]{10,200}>', html)
for inp in inputs[:30]:
    print(f'  {inp[:200]}')

print('\n=== Select elements ===')
selects = re.findall(r'<select[^>]{0,200}>', html)
for sel in selects[:20]:
    print(f'  {sel[:200]}')

print('\n=== Ant Design option items ===')
options = re.findall(r'li[^>]*role=option[^>]*>[^<]{1,60}', html)
for opt in options[:20]:
    print(f'  {opt[:120]}')
