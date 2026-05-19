"""
Probe the BMKG sinoptik form in two scenarios:
  A) New / empty form  (hour that has never been submitted today)
  B) Pre-filled form   (hour that was already submitted — loads in edit mode)

Captures the full HTML and all button labels for each, so we can understand
exactly what changes between the two modes.
"""
import os, re
from datetime import date as _date, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

RESULTS  = Path("e2e_results/form_mode_probe")
RESULTS.mkdir(parents=True, exist_ok=True)
USER_DIR = os.path.join(os.path.expanduser("~"), "bmkg_browser_data")
URL      = "https://bmkgsatu.bmkg.go.id/meteorologi/sinoptik"
TIMEOUT  = 15_000

def dump(page, label):
    path = RESULTS / f"{label}.html"
    path.write_text(page.content(), encoding="utf-8")
    page.screenshot(path=str(RESULTS / f"{label}.png"))

def setup_station_and_date(page, target_date):
    from src.core.autoinput import _select_calendar_date
    page.goto(URL, timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=30_000)
    page.wait_for_timeout(2000)
    page.locator("#select-station div").nth(1).click(timeout=TIMEOUT)
    page.get_by_role("option", name=re.compile(r"^Stasiun")).click(timeout=TIMEOUT)
    page.wait_for_timeout(600)
    page.locator("#input-datepicker__value_").click(timeout=TIMEOUT)
    page.wait_for_timeout(500)
    _select_calendar_date(page, target_date, timeout=TIMEOUT)
    page.wait_for_timeout(500)

def select_hour(page, hour: int):
    page.locator("#input-jam div").nth(1).click(timeout=TIMEOUT)
    page.locator("#input-jam").get_by_role("textbox").fill(str(hour))
    page.locator("#input-jam").get_by_role("textbox").press("Enter")
    page.wait_for_load_state("networkidle", timeout=20_000)
    page.wait_for_timeout(2000)

def analyze_form(page, label):
    html = page.content()
    dump(page, label)

    # All buttons
    btns = re.findall(r'<button[^>]*>(.*?)</button>', html, re.DOTALL)
    btn_texts = []
    for b in btns:
        t = re.sub(r'<[^>]+>', '', b).strip()
        t = re.sub(r'\s+', ' ', t)
        if t and len(t) < 80:
            btn_texts.append(t)
    btn_texts = list(dict.fromkeys(btn_texts))  # deduplicate, preserve order

    # All input field values
    inputs = re.findall(r'<input[^>]+id="([^"]+)"[^>]+value="([^"]*)"', html)

    # Ant Design dropdown selected values (title attribute)
    ant_values = re.findall(r'id="([^"]+)"[^>]*>.*?<div title="([^"]*)"', html)

    # Check wind indicator value
    wind_iw = re.search(r'wind_indicator_iw.{0,200}', html)
    wind_val = ''
    if wind_iw:
        t = re.search(r'title="([^"]+)"', wind_iw.group())
        wind_val = t.group(1) if t else ''

    # CL dominant value
    cl_m = re.search(r'cloud_low_type_cl.{0,200}', html)
    cl_val = ''
    if cl_m:
        t = re.search(r'title="([^"]+)"', cl_m.group())
        cl_val = t.group(1) if t else ''

    # Layer 2 toggle state
    toggle = 'checked' if 'switch-icon-right' in html and 'custom-control-input:checked' in html else 'unchecked'

    print(f"\n=== {label} ===")
    print(f"  Buttons: {btn_texts}")
    print(f"  Wind indicator: {wind_val!r}")
    print(f"  CL dominant: {cl_val!r}")
    print(f"  Input field values (id -> value):")
    for fid, val in inputs:
        if val and fid not in ('loading-bg',):
            print(f"    {fid}: {val!r}")
    print(f"  Layer 2 toggle: {toggle}")

    return {"buttons": btn_texts, "wind_iw": wind_val, "cl": cl_val}

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=USER_DIR,
        headless=False,
        slow_mo=200,
        args=["--no-sandbox"],
        no_viewport=True,
    )
    page = ctx.new_page()
    page.set_viewport_size({"width": 1600, "height": 900})

    today = _date.today()
    yesterday = today - timedelta(days=1)

    # ── Mode A: today + a likely-fresh hour (2am) ──────────────────────────
    print("\nProbing MODE A: today + hour 2 (likely empty/new)")
    setup_station_and_date(page, today)
    select_hour(page, 2)
    mode_a = analyze_form(page, "mode_A_today_hour2")

    # ── Mode B: yesterday + hour 0 (likely previously submitted) ───────────
    print("\nProbing MODE B: yesterday + hour 0 (likely pre-filled/edit)")
    setup_station_and_date(page, yesterday)
    select_hour(page, 0)
    mode_b = analyze_form(page, "mode_B_yesterday_hour0")

    # ── Mode C: today + current hour (might have data if already submitted) ─
    import datetime
    current_hour = datetime.datetime.now().hour
    print(f"\nProbing MODE C: today + current hour {current_hour} (may be filled)")
    setup_station_and_date(page, today)
    select_hour(page, current_hour)
    mode_c = analyze_form(page, f"mode_C_today_hour{current_hour}")

    ctx.close()

    print("\n=== COMPARISON ===")
    print(f"Mode A buttons: {mode_a['buttons']}")
    print(f"Mode B buttons: {mode_b['buttons']}")
    print(f"Mode C buttons: {mode_c['buttons']}")
    print(f"\nResults saved to: {RESULTS}/")
