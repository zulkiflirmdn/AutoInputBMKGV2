"""
Probe two specific dropdowns on the live BMKG form:
  1. Observer (#select-observer) — check enabled/disabled, list options
  2. CL Lapisan 1 type — open and capture ALL option texts

Run: python probe_dropdowns.py
"""
import os, re
from datetime import date as _date
from pathlib import Path
from playwright.sync_api import sync_playwright

RESULTS  = Path("e2e_results/dropdown_probe")
RESULTS.mkdir(parents=True, exist_ok=True)
USER_DIR = os.path.join(os.path.expanduser("~"), "bmkg_browser_data")
URL      = "https://bmkgsatu.bmkg.go.id/meteorologi/sinoptik"
TIMEOUT  = 15_000

def dump(page, label):
    path = RESULTS / f"{label}.html"
    path.write_text(page.content(), encoding="utf-8")
    page.screenshot(path=str(RESULTS / f"{label}.png"))
    return path

def get_open_dropdown_options(page):
    """Return all text items from the currently-open Ant Design dropdown."""
    html = page.content()
    # Ant Design v3 option items
    items = re.findall(
        r'<li[^>]*role=["\']option["\'][^>]*>\s*(.*?)\s*</li>',
        html, re.DOTALL
    )
    # Also try the dropdown menu items without role
    items2 = re.findall(
        r'class=["\']ant-select-dropdown-menu-item[^"\']*["\'][^>]*>\s*(.*?)\s*</li>',
        html, re.DOTALL
    )
    all_items = items + items2
    cleaned = []
    for i in all_items:
        t = re.sub(r'<[^>]+>', '', i).strip()
        t = re.sub(r'\s+', ' ', t)
        if t:
            cleaned.append(t)
    return list(dict.fromkeys(cleaned))   # deduplicate

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=USER_DIR,
        headless=False,
        slow_mo=300,
        args=["--no-sandbox"],
        no_viewport=True,
    )
    page = ctx.new_page()
    page.set_viewport_size({"width": 1600, "height": 900})

    print("Navigating to Sinoptik...")
    page.goto(URL, timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=30_000)
    page.wait_for_timeout(2000)

    # Select station first
    page.locator("#select-station div").nth(1).click(timeout=TIMEOUT)
    page.get_by_role("option", name=re.compile(r"^Stasiun")).click(timeout=TIMEOUT)
    page.wait_for_timeout(1000)

    # ── 1. Probe observer ──────────────────────────────────────────────────
    print("\n=== OBSERVER DROPDOWN ===")
    obs_el = page.locator("#select-observer")
    obs_class = obs_el.get_attribute("class") or ""
    is_disabled = "ant-select-disabled" in obs_class
    print(f"  CSS class: {obs_class}")
    print(f"  Disabled : {is_disabled}")

    if is_disabled:
        print("  Observer is auto-populated — reading current value:")
        title_el = obs_el.locator("[title]").first
        current_val = title_el.get_attribute("title") if title_el.count() > 0 else "(no title attr)"
        print(f"  Current value: {current_val!r}")
    else:
        print("  Observer IS enabled — opening to read options...")
        page.locator("#select-observer div").nth(1).click(timeout=TIMEOUT)
        page.wait_for_timeout(600)
        dump(page, "observer_open")
        opts = get_open_dropdown_options(page)
        print(f"  Options ({len(opts)}):")
        for o in opts:
            print(f"    {o!r}")
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

    # ── 2. Select date + hour so cloud fields appear ───────────────────────
    print("\n=== Setting up form (date + hour) to reveal cloud fields ===")
    from src.core.autoinput import _select_calendar_date
    page.locator("#input-datepicker__value_").click(timeout=TIMEOUT)
    page.wait_for_timeout(500)
    _select_calendar_date(page, _date.today(), timeout=TIMEOUT)
    page.wait_for_timeout(500)

    page.locator("#input-jam div").nth(1).click(timeout=TIMEOUT)
    page.locator("#input-jam").get_by_role("textbox").fill("2")
    page.locator("#input-jam").get_by_role("textbox").press("Enter")
    page.wait_for_load_state("networkidle", timeout=20_000)
    page.wait_for_timeout(1500)

    # Handle SweetAlert if present
    swal = page.locator(".swal2-popup")
    if swal.count() > 0 and swal.first.is_visible():
        page.locator(".swal2-confirm").first.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        print("  SweetAlert dismissed")

    # Set CL dominant to something non-zero so NCL/CL layer fields appear
    print("\n  Setting CL dominant to reveal layer fields...")
    page.locator("#cloud_low_type_cl div").nth(1).click(timeout=TIMEOUT)
    page.wait_for_timeout(600)
    dump(page, "cl_dominant_open")
    opts_cl = get_open_dropdown_options(page)
    print(f"  CL dominant options ({len(opts_cl)}):")
    for o in opts_cl:
        print(f"    {o!r}")
    # pick the first non-zero option
    if opts_cl:
        first_opt = opts_cl[0]
        page.get_by_role("option", name=first_opt).click(timeout=TIMEOUT)
        print(f"  Selected CL dominant: {first_opt!r}")
    else:
        page.keyboard.press("Escape")

    page.wait_for_timeout(1000)

    # ── 3. Probe CL lapisan 1 type dropdown ──────────────────────────────
    print("\n=== CL LAPISAN 1 TYPE DROPDOWN ===")
    dump(page, "before_cl1_open")

    # The selector used in autoinput.py
    cl1_sel = "div:nth-child(3) > .ant-select > .ant-select-selection"
    cl1_locator = page.locator(cl1_sel).first

    # Check how many elements match
    count = page.locator(cl1_sel).count()
    print(f"  Selector '{cl1_sel}' matches: {count} element(s)")

    if count > 0:
        # Get info on all matching elements
        for i in range(min(count, 6)):
            el = page.locator(cl1_sel).nth(i)
            title = el.evaluate("e => e.closest('[id]')?.id || e.getAttribute('title') || ''")
            cls = el.get_attribute("class") or ""
            print(f"  [{i}] id={title!r} class_snippet={cls[:60]!r}")

        print("\n  Opening CL lapisan 1 dropdown (nth 0)...")
        page.locator(cl1_sel).first.click(timeout=TIMEOUT)
        page.wait_for_timeout(800)
        dump(page, "cl1_type_open")

        opts_cl1 = get_open_dropdown_options(page)
        print(f"  CL lapisan 1 options ({len(opts_cl1)}):")
        for o in opts_cl1:
            print(f"    {o!r}")

        page.keyboard.press("Escape")

    # ── 4. Also probe CM layer type dropdown ─────────────────────────────
    print("\n=== CM LAYER TYPE DROPDOWN (col-4 > nth-3) ===")
    cm_sel = ".col-4 > div:nth-child(3) > .ant-select > .ant-select-selection"
    cm_count = page.locator(cm_sel).count()
    print(f"  Selector matches: {cm_count}")
    if cm_count > 0:
        page.locator(cm_sel).first.click(timeout=TIMEOUT)
        page.wait_for_timeout(600)
        dump(page, "cm_type_open")
        opts_cm = get_open_dropdown_options(page)
        print(f"  CM options: {opts_cm}")
        page.keyboard.press("Escape")

    ctx.close()
    print(f"\nProbe files saved to: {RESULTS}/")
