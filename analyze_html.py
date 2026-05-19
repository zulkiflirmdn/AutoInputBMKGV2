"""Analyze sinoptik.htm to extract form structure."""
import re

with open('sinoptik.htm', 'r', encoding='utf-8') as f:
    html = f.read()

print(f'File size: {len(html):,} chars\n')

# All IDs
ids = re.findall(r'id=(["\w\-\_]+)', html)
clean_ids = []
for i in ids:
    i = i.strip('"\'')
    if re.match(r'^[a-zA-Z][a-zA-Z0-9_\-]{3,}$', i):
        clean_ids.append(i)
unique_ids = sorted(set(clean_ids))
print(f'=== ALL IDs ({len(unique_ids)} unique) ===')
for i in unique_ids:
    print(f'  {i}')

# All labels
print('\n=== LABEL TEXT (for= attrs) ===')
labels = re.findall(r'for=(["\w\-\_]+)', html)
unique_labels = sorted(set(l.strip('"\'') for l in labels))
for l in unique_labels:
    print(f'  {l}')

# Buttons
print('\n=== BUTTONS ===')
btns = re.findall(r'<button[^>]*>([^<]{2,60})</button>', html)
for b in set(btns):
    print(f'  {b.strip()}')

# ant-select patterns
print('\n=== ANT-SELECT CLASSES (unique) ===')
ant_classes = re.findall(r'class="([^"]*ant-select[^"]*)"', html)
unique_ant = sorted(set(ant_classes))
for a in unique_ant[:20]:
    print(f'  {a}')

# Look for Vue component names / data attributes
print('\n=== DATA-V ATTRIBUTES ===')
data_v = re.findall(r'data-v-([a-f0-9]+)', html)
print(f'  Vue component hashes: {sorted(set(data_v))[:10]}')

# Look for role=combobox elements
print('\n=== COMBOBOX ELEMENTS ===')
combos = re.findall(r'[^>]{0,120}role=combobox[^>]{0,120}', html)
for c in combos[:15]:
    print(f'  {c.strip()[:200]}')

# Search for label text related to weather fields
print('\n=== WEATHER FIELD LABELS ===')
label_texts = re.findall(r'<label[^>]*>([^<]{5,80})</label>', html)
for lt in set(label_texts):
    lt = lt.strip()
    if lt:
        print(f'  {lt}')
