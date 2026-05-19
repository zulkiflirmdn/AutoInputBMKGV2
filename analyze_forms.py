"""
Comprehensive analysis of BMKG form HTML to map current selectors.
Checks both the complete sinoptik form and the METAR form.
"""
import re

def analyze_file(filename, title):
    print(f'\n{"="*70}')
    print(f'  {title}: {filename}')
    print(f'{"="*70}')

    with open(filename, 'r', encoding='utf-8') as f:
        html = f.read()
    print(f'  File size: {len(html):,} chars\n')

    def find(pattern, label='', chars=400):
        m = re.search(pattern, html)
        if m:
            s = max(0, m.start() - chars//3)
            e = min(len(html), m.end() + chars*2//3)
            snippet = re.sub(r'\s+', ' ', html[s:e])
            return True, snippet[:600]
        return False, None

    def findall(pattern, chars=200):
        results = []
        for m in re.finditer(pattern, html):
            s = max(0, m.start() - 30)
            e = min(len(html), m.end() + chars)
            snippet = re.sub(r'\s+', ' ', html[s:e])
            results.append(snippet[:300])
        return results

    # ---- IDs ----
    ids = sorted(set(re.findall(r'\bid=(["\w\-\_]+)', html)))
    clean_ids = [i.strip('"\'') for i in ids if re.match(r'^[a-zA-Z][a-zA-Z0-9_\-]{3,}$', i.strip('"\''))]
    print(f'ALL IDs ({len(clean_ids)}):')
    for i in clean_ids:
        print(f'  {i}')

    # ---- Label texts ----
    print(f'\nLABEL TEXTS:')
    label_texts = re.findall(r'<label[^>]*>(.*?)</label>', html, re.DOTALL)
    seen = set()
    for lt in label_texts:
        clean = re.sub(r'<[^>]+>', '', lt).strip()
        clean = re.sub(r'\s+', ' ', clean)
        if 3 < len(clean) < 100 and clean not in seen:
            seen.add(clean)
            safe = clean.encode('ascii', errors='replace').decode('ascii')
            print(f'  "{safe}"')

    # ---- Comboboxes ----
    print(f'\nCOMBOBOX/SELECT ELEMENTS:')
    combos = findall(r'role=["\']?combobox["\']?', 300)
    for c in combos:
        print(f'  {c[:250]}')

    # ---- Input elements ----
    print(f'\nINPUT ELEMENTS (non-radio/checkbox):')
    inputs = re.findall(r'<input[^>]+>', html)
    for inp in inputs:
        if 'type=radio' in inp or 'type=checkbox' in inp or 'type=hidden' in inp:
            continue
        print(f'  {inp[:200]}')

    # ---- Buttons ----
    print(f'\nBUTTONS:')
    btns = re.findall(r'<button[^>]*>(.*?)</button>', html, re.DOTALL)
    seen_btns = set()
    for b in btns:
        t = re.sub(r'<[^>]+>', '', b).strip()
        t = re.sub(r'\s+', ' ', t)
        if t and t not in seen_btns and len(t) < 80:
            seen_btns.add(t)
            print(f'  "{t}"')

    # ---- Ant Design dropdown items currently visible ----
    print(f'\nANT-DESIGN OPTION ITEMS (rendered):')
    options = re.findall(
        r'li[^>]*ant-select-dropdown-menu-item[^>]*>\s*([^<]{1,80})', html
    )
    for opt in options[:30]:
        print(f'  option: {opt.strip()}')

    # ---- Vue-select option items ----
    print(f'\nVUE-SELECT OPTION ITEMS:')
    vs_options = re.findall(r'<li[^>]*vs__dropdown-option[^>]*>([^<]{1,80})', html)
    for opt in vs_options[:30]:
        print(f'  vs-option: {opt.strip()}')

    # ---- All name= attributes on form elements ----
    print(f'\nFORM FIELD NAMES:')
    names = re.findall(r'\bname=["\']?([a-zA-Z0-9_\-]+)["\']?', html)
    for n in sorted(set(names)):
        print(f'  {n}')

    # ---- Ant Design version check ----
    print(f'\nANT DESIGN VERSION CHECK:')
    v3 = ['ant-select-selection--single', 'ant-select-search__field', 'ant-select-selection__rendered']
    v4 = ['ant-select-selector', 'ant-select-selection-item', 'ant-select-selection-search-input']
    for c in v3:
        print(f'  v3 "{c}": {"YES" if c in html else "no"}')
    for c in v4:
        print(f'  v4 "{c}": {"YES" if c in html else "no"}')

    # ---- Specific fields needed by autoinput.py ----
    print(f'\nSPECIFIC FIELD CHECK (autoinput.py selectors):')
    checks = [
        ('wind_indicator_iw', 'Wind Indicator (iw)'),
        ('present_weather_ww', 'Present Weather (ww)'),
        ('past_weather_w1', 'Past Weather W1'),
        ('past_weather_w2', 'Past Weather W2'),
        ('cloud_low_type_cl', 'Cloud Low CL'),
        ('cloud_low_cover_oktas', 'NCL Oktas'),
        ('cloud_low_base_1', 'Cloud Low Base'),
        ('cloud_low_peak_1', 'Cloud Low Peak'),
        ('cloud_elevation_1_angle_ec', 'Elevation Angle EC'),
        ('cloud_med_type_cm', 'Cloud Medium CM'),
        ('cloud_med_cover_oktas', 'NCM Oktas'),
        ('cloud_med_base_1', 'Cloud Med Base'),
        ('cloud_high_type_ch', 'Cloud High CH'),
        ('cloud_high_cover_oktas', 'NCH Oktas'),
        ('cloud_high_base_1', 'Cloud High Base'),
        ('land_cond', 'Land Condition'),
        ('cloud_cover_oktas_m', 'Total Cloud Oktas'),
        ('evaporation_eq_indicator_ie', 'Evaporation IE'),
        ('switch-icon-right', 'Layer 2 Toggle'),
        ('collapse-row-2', 'Collapse Row 2 (high cloud)'),
    ]
    for pattern, label in checks:
        found, ctx = find(pattern, chars=300)
        status = 'FOUND' if found else 'MISSING'
        print(f'  [{status}] {label} ({pattern})')
        if found and ctx:
            print(f'    {ctx[:300]}')

# Run on both files
analyze_file('compleate-sinoptik.htm', 'COMPLETE SINOPTIK FORM')
analyze_file('metar.htm', 'METAR FORM')
