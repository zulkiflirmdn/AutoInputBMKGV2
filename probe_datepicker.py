"""
Probe the BMKG datepicker to understand its exact behaviour for:
  - today's date
  - yesterday (same month)
  - a date in the previous month
Captures full calendar HTML at each attempt so we can read the exact structure.
"""
import os, re
from datetime import date, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

RESULTS     = Path("e2e_results/datepicker_probe")
RESULTS.mkdir(parents=True, exist_ok=True)
USER_DIR    = os.path.join(os.path.expanduser("~"), "bmkg_browser_data")
URL         = "https://bmkgsatu.bmkg.go.id/meteorologi/sinoptik"
TIMEOUT     = 15_000

def dump(page, label):
    path = RESULTS / f"{label}.html"
    path.write_text(page.content(), encoding="utf-8")
    page.screenshot(path=str(RESULTS / f"{label}.png"))
    print(f"  saved: {label}")
    return path

def open_calendar(page):
    """Click the calendar toggle button to open the picker."""
    page.locator("#input-datepicker__value_").click(timeout=TIMEOUT)
    page.wait_for_timeout(800)

def close_calendar(page):
    """Press Escape to close without selecting."""
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)

def extract_calendar(page):
    """Return dict describing the open calendar state."""
    html = page.content()
    # Find calendar nav title (current month/year shown)
    title = re.search(r'role="heading"[^>]*>\s*([^<]+)\s*</div>', html)
    # Collect all day cells
    cells = re.findall(
        r'data-date="([^"]+)"[^>]*aria-hidden="([^"]*)"[^>]*aria-label="([^"]*)"[^>]*class="([^"]*)"',
        html
    )
    # Find "today" cell - Bootstrap-Vue marks it with btn-outline-primary or similar
    today_cell = [c for c in cells if "btn-outline-primary" in c[3] or "text-primary" in c[3] or "today" in c[3].lower()]
    return {
        "month_title": title.group(1).strip() if title else "not found",
        "total_cells": len(cells),
        "today_candidates": today_cell,
        "all_dates": [(c[0], c[1], c[2]) for c in cells],  # (data-date, aria-hidden, aria-label)
    }

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=USER_DIR,
        headless=False,
        slow_mo=200,
        args=["--no-sandbox", "--start-maximized"],
        no_viewport=True,
    )
    page = ctx.new_page()
    page.set_viewport_size({"width": 1600, "height": 900})

    print("Navigating...")
    page.goto(URL, timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=30_000)
    page.wait_for_timeout(2000)

    # Select station first so date becomes enabled
    page.locator("#select-station div").nth(1).click(timeout=TIMEOUT)
    page.get_by_role("option", name=re.compile(r"^Stasiun")).click(timeout=TIMEOUT)
    page.wait_for_timeout(1000)

    today   = date.today()
    yest    = today - timedelta(days=1)
    prev_m  = today.replace(day=1) - timedelta(days=1)   # last day of previous month

    for target, label in [
        (today,  "today"),
        (yest,   "yesterday"),
        (prev_m, "prev_month_last_day"),
    ]:
        print(f"\n--- Probing: {target} ({label}) ---")
        open_calendar(page)
        dump(page, f"calendar_open_{label}")
        info = extract_calendar(page)
        print(f"  Month shown : {info['month_title']}")
        print(f"  Total cells : {info['total_cells']}")
        print(f"  Today candidates: {info['today_candidates']}")

        # Check if target date is directly visible
        target_str = target.strftime("%Y-%m-%d")
        visible = [d for d in info["all_dates"] if d[0] == target_str]
        print(f"  Target {target_str}: {visible if visible else 'NOT in calendar'}")

        # Show all date cells with their aria-hidden and aria-label
        print(f"  All cells (date, aria-hidden, aria-label):")
        for d in info["all_dates"]:
            print(f"    {d[0]}  hidden={d[1]!r:6s}  label={d[2]!r}")

        close_calendar(page)
        page.wait_for_timeout(500)

    # Additional: actually try selecting yesterday to see if it succeeds
    print("\n--- Actually selecting YESTERDAY ---")
    open_calendar(page)
    yest_str = yest.strftime("%Y-%m-%d")
    el = page.locator(f'[data-date="{yest_str}"]')
    print(f"  Locator count for {yest_str}: {el.count()}")
    if el.count() > 0:
        props = page.evaluate(f"""
            (() => {{
                const el = document.querySelector('[data-date="{yest_str}"]');
                if (!el) return null;
                return {{
                    ariaHidden: el.getAttribute('aria-hidden'),
                    ariaDisabled: el.getAttribute('aria-disabled'),
                    classes: el.className,
                    role: el.getAttribute('role'),
                    visible: el.offsetParent !== null,
                }};
            }})()
        """)
        print(f"  Element props: {props}")
    dump(page, "calendar_yesterday_attempt")
    close_calendar(page)

    ctx.close()
    print(f"\nProbe results saved to: {RESULTS}/")
