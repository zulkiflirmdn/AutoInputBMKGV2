"""Verify specific selector paths used in autoinput.py against the live HTML."""
import re

with open('sinoptik.htm', 'r', encoding='utf-8') as f:
    html = f.read()

def find_context(pattern, label, chars=500):
    m = re.search(pattern, html)
    if m:
        start = max(0, m.start() - chars//2)
        end = min(len(html), m.end() + chars//2)
        snippet = html[start:end]
        snippet = re.sub(r'\s+', ' ', snippet)
        print(f'  [FOUND] {label}')
        print(f'  {snippet[:500]}')
    else:
        print(f'  [MISSING] {label}')
    print()

print('='*60)
print('SELECTOR VERIFICATION vs sinoptik.htm')
print('='*60)

print('\n--- HEADER FIELDS (confirmed in HTML) ---')
find_context(r'id=select-station', '#select-station')
find_context(r'id=select-observer', '#select-observer')
find_context(r'id=input-jam', '#input-jam')
find_context(r'id=input-datepicker__value_', '#input-datepicker__value_')

print('\n--- WEATHER FIELDS (dynamic, require login+interaction) ---')
for fid in [
    'wind_indicator_iw', 'present_weather_ww', 'past_weather_w1', 'past_weather_w2',
    'cloud_low_type_cl', 'cloud_low_cover_oktas', 'cloud_low_base_1',
    'cloud_med_type_cm', 'cloud_high_type_ch', 'land_cond',
    'cloud_cover_oktas_m', 'evaporation_eq_indicator_ie',
]:
    find_context(fid, f'#{fid}')

print('\n--- ANT DESIGN VERSION CHECK ---')
v3_classes = ['ant-select-selection--single', 'ant-select-search__field', 'ant-select-selection__rendered']
v4_classes = ['ant-select-selector', 'ant-select-selection-item', 'ant-select-selection-search-input']
for c in v3_classes:
    found = c in html
    print(f'  v3: {c} -> {"PRESENT" if found else "absent"}')
for c in v4_classes:
    found = c in html
    print(f'  v4: {c} -> {"PRESENT" if found else "absent"}')

print('\n--- COMBOBOX CLICK TARGET VERIFICATION ---')
print('  Code does: page.locator("#select-station div").nth(1).click()')
m = re.search(r'id=select-station[^>]*>(.*?)</div></div></div>', html, re.DOTALL)
if m:
    inner = m.group(1)
    divs = re.findall(r'<div[^>]*>', inner)
    for i, d in enumerate(divs[:6]):
        print(f'  div.nth({i}): {d[:120]}')

print('\n--- OPTION ITEMS IN DROPDOWNS ---')
options = re.findall(r'li[^>]*class=["\']?[^"\']*ant-select-dropdown-menu-item[^"\']*["\']?[^>]*>([^<]{1,80})', html)
if options:
    for opt in options[:10]:
        print(f'  option: {opt.strip()}')
else:
    print('  No option items rendered (dropdowns are closed in this capture)')

print('\n--- PAGE STATE SUMMARY ---')
disabled_count = html.count('ant-select-disabled')
enabled_count = html.count('ant-select-enabled')
print(f'  ant-select-enabled fields: {enabled_count}')
print(f'  ant-select-disabled fields: {disabled_count}')
print()
if 'login' in html.lower() or 'masuk' in html.lower() or 'sign in' in html.lower():
    print('  LOGIN FORM DETECTED in HTML')
else:
    print('  No login form found — page is partially loaded (pre-interaction state)')

# Check what page title / meta says
title = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL)
if title:
    print(f'  Page title: {title.group(1).strip()}')
