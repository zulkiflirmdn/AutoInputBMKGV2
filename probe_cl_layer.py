"""
Precise probe:
 - Read observer value AFTER hour is selected (form fully loaded)
 - Open CL lapisan 1 type dropdown and read its options via JS (not DOM scrape)
"""
import os, re
from datetime import date as _date
from pathlib import Path
from playwright.sync_api import sync_playwright

RESULTS  = Path("e2e_results/cl_layer_probe")
RESULTS.mkdir(parents=True, exist_ok=True)
USER_DIR = os.path.join(os.path.expanduser("~"), "bmkg_browser_data")
URL      = "https://bmkgsatu.bmkg.go.id/meteorologi/sinoptik"
TIMEOUT  = 15_000

def get_visible_dropdown_options(page):
    """Get options ONLY from the currently-visible Ant Design v3 dropdown."""
    return page.evaluate("""
        () => {
            // Find the dropdown that is currently visible (not display:none)
            const dropdowns = document.querySelectorAll('.ant-select-dropdown');
            for (const dd of dropdowns) {
                const style = window.getComputedStyle(dd);
                if (style.display !== 'none' && style.visibility !== 'hidden') {
                    const items = dd.querySelectorAll('.ant-select-dropdown-menu-item');
                    return Array.from(items).map(el => ({
                        text: el.textContent.trim(),
                        classes: el.className,
                        selected: el.classList.contains('ant-select-dropdown-menu-item-selected')
                    }));
                }
            }
            return [];
        }
    """)

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

    from src.core.autoinput import _select_calendar_date

    print("Navigating...")
    page.goto(URL, timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=30_000)
    page.wait_for_timeout(2000)

    # Station
    page.locator("#select-station div").nth(1).click(timeout=TIMEOUT)
    page.get_by_role("option", name=re.compile(r"^Stasiun")).click(timeout=TIMEOUT)
    page.wait_for_timeout(800)

    # Date
    page.locator("#input-datepicker__value_").click(timeout=TIMEOUT)
    page.wait_for_timeout(400)
    _select_calendar_date(page, _date.today(), timeout=TIMEOUT)
    page.wait_for_timeout(400)

    # Hour
    page.locator("#input-jam div").nth(1).click(timeout=TIMEOUT)
    page.locator("#input-jam").get_by_role("textbox").fill("2")
    page.locator("#input-jam").get_by_role("textbox").press("Enter")
    page.wait_for_load_state("networkidle", timeout=20_000)
    page.wait_for_timeout(2000)

    # SweetAlert
    swal = page.locator(".swal2-popup")
    if swal.count() > 0 and swal.first.is_visible():
        page.locator(".swal2-confirm").first.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)

    # ── Read observer AFTER form loads ─────────────────────────────────────
    print("\n=== OBSERVER after hour selected ===")
    obs_el = page.locator("#select-observer")
    obs_class = obs_el.get_attribute("class") or ""
    title_div = obs_el.locator(".ant-select-selection-selected-value").first
    current_val = title_div.get_attribute("title") or title_div.text_content() or "(empty)"
    print(f"  Class    : {obs_class!r}")
    print(f"  Value    : {current_val!r}")

    if "ant-select-disabled" not in obs_class:
        print("  => Observer IS enabled, opening to list options...")
        page.locator("#select-observer div").nth(1).click(timeout=TIMEOUT)
        page.wait_for_timeout(500)
        opts = get_visible_dropdown_options(page)
        print(f"  Options ({len(opts)}):")
        for o in opts:
            print(f"    {o['text']!r}  selected={o['selected']}")
        page.keyboard.press("Escape")
    else:
        print("  => Observer is disabled (auto-populated from session)")

    # ── Set CL dominant (use textbox approach) ────────────────────────────
    print("\n=== Setting CL dominant = 5 (SC) ===")
    page.locator("#cloud_low_type_cl div").nth(1).click(timeout=TIMEOUT)
    page.locator("#cloud_low_type_cl").get_by_role("textbox").fill("5")
    page.locator("#cloud_low_type_cl").get_by_role("textbox").press("Enter")
    page.wait_for_timeout(600)

    # ── Set NCL = 5 ────────────────────────────────────────────────────────
    print("=== Setting NCL = 5 ===")
    page.locator("#cloud_low_cover_oktas div").nth(1).click(timeout=TIMEOUT)
    page.locator("#cloud_low_cover_oktas").get_by_role("textbox").fill("5")
    page.locator("#cloud_low_cover_oktas").get_by_role("textbox").press("Enter")
    page.wait_for_timeout(600)

    # ── Count all matching selectors ─────────────────────────────────────
    sel = "div:nth-child(3) > .ant-select > .ant-select-selection"
    count = page.locator(sel).count()
    print(f"\n=== Selector '{sel}' matches {count} elements ===")
    for i in range(min(count, 8)):
        el  = page.locator(sel).nth(i)
        box = el.bounding_box()
        title = el.evaluate(
            "e => e.closest('[id]')?.id + ' | ' + (e.querySelector('[title]')?.getAttribute('title') || '')"
        )
        visible = el.is_visible()
        print(f"  [{i}] visible={visible}  parent_id+title={title!r}  box={box}")

    # ── Open the FIRST visible CL layer type selector and read options ────
    print("\n=== CL LAPISAN 1 TYPE — opening nth(0) ===")
    # Find the first VISIBLE ant-select inside the low cloud layer section
    # Use JS to identify which element to click
    layer_selects = page.evaluate("""
        () => {
            const cols = document.querySelectorAll('.col-sm-1, .row.mt-1, .row.pr-1');
            const selects = document.querySelectorAll('.ant-select');
            const results = [];
            for (const s of selects) {
                const box = s.getBoundingClientRect();
                if (box.width > 0 && box.height > 0) {
                    const id = s.id || s.closest('[id]')?.id || '';
                    const selected = s.querySelector('.ant-select-selection-selected-value');
                    results.push({
                        id: id,
                        title: selected?.getAttribute('title') || '',
                        x: box.x, y: box.y, w: box.width
                    });
                }
            }
            return results;
        }
    """)
    print(f"  All visible ant-select elements ({len(layer_selects)}):")
    for s in layer_selects:
        print(f"    id={s['id']!r:30s} title={s['title']!r:25s} x={s['x']:.0f} y={s['y']:.0f}")

    # ── Click the cloud-layer-type selector (right after NCL) ─────────────
    # The first .ant-select that is NOT a known named one and is after NCL
    known_ids = {
        "select-station","select-observer","input-jam",
        "wind_indicator_iw","input-cuaca-ix",
        "present_weather_ww","past_weather_w1","past_weather_w2",
        "cloud_cover_oktas_m","cloud_low_type_cl","cloud_low_cover_oktas",
        "cloud_elevation_1_angle_ec","cloud_elevation_2_angle_ec",
        "cloud_med_type_cm","cloud_med_cover_oktas",
        "cloud_high_type_ch","cloud_high_cover_oktas","land_cond",
        "evaporation_eq_indicator_ie",
    }
    unnamed = [s for s in layer_selects if s['id'] not in known_ids]
    print(f"\n  Unnamed selects (layer type/count/direction) ({len(unnamed)}):")
    for s in unnamed:
        print(f"    id={s['id']!r:20s} title={s['title']!r:25s} x={s['x']:.0f} y={s['y']:.0f}")

    # Click the first unnamed select (should be CL lapisan 1 type)
    if unnamed:
        first = unnamed[0]
        print(f"\n  Clicking first unnamed select: x={first['x']:.0f} y={first['y']:.0f}")
        page.mouse.click(first['x'] + first['w']//2, first['y'] + 10)
        page.wait_for_timeout(800)
        page.screenshot(path=str(RESULTS / "cl1_type_dropdown_open.png"))

        opts = get_visible_dropdown_options(page)
        print(f"\n=== CL LAPISAN 1 TYPE OPTIONS ({len(opts)}) ===")
        for o in opts:
            print(f"  {o['text']!r}  selected={o['selected']}")
        page.keyboard.press("Escape")

    ctx.close()
    print(f"\nDone. Results: {RESULTS}/")
