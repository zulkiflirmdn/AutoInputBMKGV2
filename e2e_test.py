"""
End-to-end Playwright test for BMKG Sinoptik form.

Walks through every field interaction, captures HTML snapshots and screenshots
at each step, and reports exactly where the automation breaks.

Run:  python e2e_test.py
Results saved to:  e2e_results/
"""
import os, re, time, traceback, json
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from src.data.sandi import (
    obs, ww, w1w2, awan_lapisan, arah_angin, ci, cm, ch,
    default_user_input, STATION_CODE, DEFAULT_OBSERVER,
)

# ── Output dir ──────────────────────────────────────────────────────────────
RESULTS = Path("e2e_results")
RESULTS.mkdir(exist_ok=True)

_default_dir = os.path.join(os.path.expanduser("~"), "bmkg_browser_data")
_test_dir    = os.path.join(os.path.expanduser("~"), "bmkg_browser_data_e2e")
USER_DATA_DIR = _test_dir if not os.path.exists(os.path.join(_default_dir, "lockfile")) else _test_dir
URL_SINOPTIK  = "https://bmkgsatu.bmkg.go.id/meteorologi/sinoptik"
TIMEOUT       = 15_000   # ms per action

# ── Helpers ──────────────────────────────────────────────────────────────────
step_num   = 0
results    = []   # list of dicts

def save_html(page, label):
    path = RESULTS / f"{step_num:03d}_{label}.html"
    path.write_text(page.content(), encoding="utf-8")
    return str(path)

def save_screenshot(page, label):
    path = RESULTS / f"{step_num:03d}_{label}.png"
    page.screenshot(path=str(path), full_page=False)
    return str(path)

def step(label, fn, page, *, capture_selector=None):
    """Run one automation step, capture evidence, record pass/fail."""
    global step_num
    step_num += 1
    print(f"\n[{step_num:03d}] {label}")
    rec = {"step": step_num, "label": label, "status": None, "error": None,
           "html": None, "screenshot": None, "captured_html": None}
    try:
        fn()
        rec["status"] = "PASS"
        rec["screenshot"] = save_screenshot(page, f"{label.replace(' ','_')}_PASS")
        if capture_selector:
            try:
                el = page.locator(capture_selector).first
                el.wait_for(state="attached", timeout=3000)
                rec["captured_html"] = el.inner_html()
            except Exception:
                pass
        print(f"    [PASS]")
    except Exception as e:
        rec["status"] = "FAIL"
        rec["error"]  = traceback.format_exc()
        rec["screenshot"] = save_screenshot(page, f"{label.replace(' ','_')}_FAIL")
        rec["html"]   = save_html(page, f"{label.replace(' ','_')}_FAIL")
        print(f"    [FAIL]: {e}")
    results.append(rec)
    return rec["status"] == "PASS"

def try_click_antd_combobox(page, element_id, value, timeout=TIMEOUT):
    """Standard Ant Design v3 combobox interaction."""
    page.locator(f"#{element_id} div").nth(1).click(timeout=timeout)
    page.locator(f"#{element_id}").get_by_role("textbox").fill(value)
    page.locator(f"#{element_id}").get_by_role("textbox").press("Enter")

def antd_select_option(page, element_id, option_name, timeout=TIMEOUT):
    """Click combobox and select by visible option text."""
    page.locator(f"#{element_id} div").nth(1).click(timeout=timeout)
    page.get_by_role("option", name=option_name).click(timeout=timeout)

# ── Test data ─────────────────────────────────────────────────────────────────
EXCEL_FILE = r"D:/ME48/2026/05 MEI/Tanggal 19.xls"
TEST_HOUR  = 12    # hour 12 UTC — has Suhu Maksimum + Hujan Ditakar

# Try loading real Excel data; fall back to defaults if file missing
ui = default_user_input.copy()
ui['jam_pengamatan'] = str(TEST_HOUR)
try:
    from src.data.user_input import UserInputUpdater
    import os
    if os.path.exists(EXCEL_FILE):
        updater = UserInputUpdater(ui.copy())
        ui = updater.update_from_file(EXCEL_FILE, TEST_HOUR, "input_data")
        print(f"Loaded data from Excel: {EXCEL_FILE}")
    else:
        print(f"Excel file not found, using defaults: {EXCEL_FILE}")
except Exception as ex:
    print(f"Could not load Excel ({ex}), using defaults")

today = datetime.now(timezone.utc)
DATE_LABEL = f"{today.month}/{today.day}/{today.year} (Today)"

obs_name  = obs.get(ui['obs_onduty'].lower(), DEFAULT_OBSERVER)
ww_value  = ww.get(ui['cuaca_pengamatan'], "00")
w1_value  = w1w2.get(ui['cuaca_w1'], "0")
w2_value  = w1w2.get(ui['cuaca_w2'], "0")
cl_value  = ci.get(ui['cl_dominan'], "0")
cm_value  = cm.get(ui['cm_awan_menengah'], "0")
ch_value  = ch.get(ui['ch_awan_tinggi'], "0")
cl1_value = awan_lapisan.get(ui['jenis_cl_lapisan1'], "8")
cm1_value = awan_lapisan.get(ui['jenis_awan_menengah'], "3")
ch1_value = awan_lapisan.get(ui['ch_awan_tinggi'], "0")
agl1      = arah_angin.get(ui['arah_gerak_aw_lapisan1'], "0")
agcm      = arah_angin.get(ui['arah_gerak_cm'], "0")
agch      = arah_angin.get(ui['arah_gerak_ch'], "0")

# ── Main test ─────────────────────────────────────────────────────────────────
with sync_playwright() as p:
    print("Launching browser (using existing session)...")
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=False,
        slow_mo=300,
        args=["--no-sandbox", "--start-maximized"],
        no_viewport=True,
    )
    page = ctx.new_page()
    page.set_viewport_size({"width": 1600, "height": 900})

    # ── 0. Navigate ──────────────────────────────────────────────────────────
    def nav():
        page.goto(URL_SINOPTIK, timeout=30_000)
        page.wait_for_load_state("networkidle", timeout=30_000)
        page.wait_for_timeout(2000)
        # Check if we're on the login page
        if "login" in page.url.lower() or "masuk" in page.url.lower():
            raise RuntimeError(f"Not logged in! Redirected to: {page.url}")
        # Check the form is present
        page.wait_for_selector("#select-station", timeout=10_000)

    step("0. Navigate to Sinoptik", nav, page)
    save_html(page, "000_initial_page")

    # ── 1. Station ────────────────────────────────────────────────────────────
    def sel_station():
        page.locator("#select-station div").nth(1).click(timeout=TIMEOUT)
        page.get_by_role("option", name=re.compile(r"^Stasiun")).click(timeout=TIMEOUT)

    step("1. Select station", sel_station, page, capture_selector="#select-station")

    # ── 2. Observer — auto-populated from login session, skip ────────────────
    print(f"\n[---] 2. Observer: auto-populated from session (disabled field), skipping")
    save_screenshot(page, "002_observer_auto")

    # ── 3. Date ───────────────────────────────────────────────────────────────
    from datetime import date as _date
    from src.core.autoinput import _select_calendar_date

    TEST_DATES = {
        "today":        _date.today(),
        "yesterday":    _date.today() - __import__('datetime').timedelta(days=1),
    }

    for date_label, target_date in TEST_DATES.items():
        def sel_date(td=target_date, dl=date_label):
            page.locator("#input-datepicker__value_").click(timeout=TIMEOUT)
            page.wait_for_timeout(500)
            save_html(page, f"003_calendar_open_{dl}")
            _select_calendar_date(page, td, timeout=TIMEOUT)

        step(f"3. Select date ({date_label}: {target_date})", sel_date, page)

        # reload the page so the calendar resets for the next date test
        if date_label != list(TEST_DATES.keys())[-1]:
            page.reload()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)
            # Re-select station for next test
            page.locator("#select-station div").nth(1).click(timeout=TIMEOUT)
            page.get_by_role("option", name=re.compile(r"^Stasiun")).click(timeout=TIMEOUT)
            page.wait_for_timeout(500)

    # ── 4. Hour ───────────────────────────────────────────────────────────────
    def sel_hour():
        page.locator("#input-jam div").nth(1).click(timeout=TIMEOUT)
        page.locator("#input-jam").get_by_role("textbox").fill(ui['jam_pengamatan'])
        page.locator("#input-jam").get_by_role("textbox").press("Enter")
        page.wait_for_load_state("networkidle", timeout=20_000)
        page.wait_for_timeout(1500)

    step(f"4. Select hour ({ui['jam_pengamatan']}:00)", sel_hour, page)
    save_html(page, "004_after_hour_selected")

    # ── 5. Wind indicator ─────────────────────────────────────────────────────
    def wind_iw():
        try_click_antd_combobox(page, "wind_indicator_iw", ui['pengenal_angin'])

    step("5. Wind indicator (iw)", wind_iw, page, capture_selector="#wind_indicator_iw")

    # ── 6. Wind direction ─────────────────────────────────────────────────────
    def wind_dir():
        page.locator("#wind_dir_deg_dd").click(timeout=TIMEOUT)
        page.locator("#wind_dir_deg_dd").fill(ui['arah_angin'])

    step("6. Wind direction (degrees)", wind_dir, page)

    # ── 7. Wind speed ─────────────────────────────────────────────────────────
    def wind_spd():
        page.locator("#wind_speed_ff").click(timeout=TIMEOUT)
        page.locator("#wind_speed_ff").fill(ui['kecepatan_angin'])

    step("7. Wind speed (knots)", wind_spd, page)

    # ── 8. Visibility ─────────────────────────────────────────────────────────
    def visibility():
        page.locator("#visibility_vv").click(timeout=TIMEOUT)
        page.locator("#visibility_vv").fill(ui['jarak_penglihatan'])

    step("8. Visibility", visibility, page)

    # ── 9. Present weather (ww) ───────────────────────────────────────────────
    def present_ww():
        page.locator("#present_weather_ww div").nth(1).click(timeout=TIMEOUT)
        page.locator("#present_weather_ww").get_by_role("textbox").fill(ww_value)
        page.locator("#present_weather_ww").get_by_role("textbox").press("Enter")

    step("9. Present weather (ww)", present_ww, page, capture_selector="#present_weather_ww")

    # ── 10. Past weather W1 ───────────────────────────────────────────────────
    def past_w1():
        page.locator("#past_weather_w1 div").nth(1).click(timeout=TIMEOUT)
        page.locator("#past_weather_w1").get_by_role("textbox").fill(w1_value)
        page.locator("#past_weather_w1").get_by_role("textbox").press("Enter")

    step("10. Past weather W1", past_w1, page)

    # ── 11. Past weather W2 ───────────────────────────────────────────────────
    def past_w2():
        page.locator("#past_weather_w2 div").nth(1).click(timeout=TIMEOUT)
        page.locator("#past_weather_w2").get_by_role("textbox").fill(w2_value)
        page.locator("#past_weather_w2").get_by_role("textbox").press("Enter")

    step("11. Past weather W2", past_w2, page)

    # ── 12. Cuaca IX — disabled/auto-calculated, skip ────────────────────────
    print(f"\n[---] 12. Cuaca IX: auto-calculated by site, skipping")
    save_html(page, "012_after_weather_fields")

    # ── Hour-12 special fields ────────────────────────────────────────────────
    jam = int(ui.get('jam_pengamatan', '0'))
    if jam == 12:
        def suhu_max():
            page.locator("#temp_max_c_txtxtx").click(timeout=TIMEOUT)
            page.locator("#temp_max_c_txtxtx").fill(ui['suhu_maksimum'])
        step("12a. Suhu Maksimum (jam 12)", suhu_max, page)

        def hujan_12():
            page.locator("#rainfall_last_mm").click(timeout=TIMEOUT)
            page.locator("#rainfall_last_mm").fill(ui['hujan_ditakar'])
        step("12b. Hujan Ditakar (jam 12)", hujan_12, page)

    elif jam == 0:
        def suhu_min():
            page.locator("#temp_min_c_tntntn").click(timeout=TIMEOUT)
            page.locator("#temp_min_c_tntntn").fill(ui['suhu_minimum'])
        step("12a. Suhu Minimum (jam 0)", suhu_min, page)

    elif jam in [3, 6, 9, 15, 18, 21]:
        def hujan_3():
            page.locator("#rainfall_last_mm").click(timeout=TIMEOUT)
            page.locator("#rainfall_last_mm").fill(ui['hujan_ditakar'])
        step(f"12b. Hujan Ditakar (jam {jam})", hujan_3, page)

    # ── 13. Pressure QFF ─────────────────────────────────────────────────────
    def qff():
        page.locator("#input_qff").click(timeout=TIMEOUT)
        page.locator("#input_qff").fill(ui['tekanan_qff'])

    step("13. Tekanan QFF", qff, page)

    # ── 14. Pressure QFE ─────────────────────────────────────────────────────
    def qfe():
        page.locator("#input_qfe").click(timeout=TIMEOUT)
        page.locator("#input_qfe").fill(ui['tekanan_qfe'])

    step("14. Tekanan QFE", qfe, page)

    # ── 15. Dry bulb temp ────────────────────────────────────────────────────
    def temp_dry():
        page.locator("#temp_drybulb_c_tttttt").click(timeout=TIMEOUT)
        page.locator("#temp_drybulb_c_tttttt").fill(ui['suhu_bola_kering'])

    step("15. Suhu Bola Kering", temp_dry, page)

    # ── 16. Wet bulb temp ────────────────────────────────────────────────────
    def temp_wet():
        page.locator("#temp_wetbulb_c").click(timeout=TIMEOUT)
        page.locator("#temp_wetbulb_c").fill(ui['suhu_bola_basah'])

    step("16. Suhu Bola Basah", temp_wet, page)
    save_html(page, "016_after_temp_fields")

    # ── 17. Total cloud oktas ────────────────────────────────────────────────
    def cloud_oktas():
        page.locator("#cloud_cover_oktas_m div").nth(1).click(timeout=TIMEOUT)
        page.locator("#cloud_cover_oktas_m").get_by_role("textbox").fill(ui['oktas'])
        page.locator("#cloud_cover_oktas_m").get_by_role("textbox").press("Enter")

    step("17. Total cloud oktas", cloud_oktas, page, capture_selector="#cloud_cover_oktas_m")

    # ── 18. CL dominant ──────────────────────────────────────────────────────
    def cl_dom():
        page.locator("#cloud_low_type_cl div").nth(1).click(timeout=TIMEOUT)
        if cl_value == "1":
            page.get_by_role("option", name="1 - cumulus humilis atau").click(timeout=TIMEOUT)
        else:
            page.locator("#cloud_low_type_cl").get_by_role("textbox").fill(cl_value)
            page.locator("#cloud_low_type_cl").get_by_role("textbox").press("Enter")

    step("18. CL dominant", cl_dom, page, capture_selector="#cloud_low_type_cl")
    save_html(page, "018_after_CL_selected")

    # ── 19. NCL total ────────────────────────────────────────────────────────
    def ncl():
        page.locator("#cloud_low_cover_oktas div").nth(1).click(timeout=TIMEOUT)
        page.locator("#cloud_low_cover_oktas").get_by_role("textbox").fill(ui['ncl_total'])
        page.locator("#cloud_low_cover_oktas").get_by_role("textbox").press("Enter")

    step("19. NCL total", ncl, page)

    # ── 20. CL Layer 1 type ───────────────────────────────────────────────────
    def cl1_type():
        page.locator("div:nth-child(3) > .ant-select > .ant-select-selection").first.click(timeout=TIMEOUT)
        page.get_by_role("option", name=cl1_value).click(timeout=TIMEOUT)

    step("20. CL Layer 1 type", cl1_type, page)
    save_html(page, "020_after_CL1_type")

    # ── 21. CL Layer 1 jumlah ─────────────────────────────────────────────────
    def cl1_count():
        page.locator("div:nth-child(4) > .ant-select > .ant-select-selection").first.click(timeout=TIMEOUT)
        page.locator("div:nth-child(4) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").first.fill(ui['jumlah_cl_lapisan1'])
        page.locator("div:nth-child(4) > .ant-select > .ant-select-selection").first.press("Enter")

    step("21. CL Layer 1 jumlah", cl1_count, page)

    # ── 22. CL Layer 1 base height ────────────────────────────────────────────
    def cl1_base():
        page.locator("#cloud_low_base_1").click(timeout=TIMEOUT)
        page.locator("#cloud_low_base_1").fill(ui['tinggi_dasar_aw_lapisan1'])

    step("22. CL Layer 1 base height", cl1_base, page)

    # ── 23. CL Layer 1 arah gerak ────────────────────────────────────────────
    def cl1_dir():
        page.locator("div:nth-child(7) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").first.click(timeout=TIMEOUT)
        page.locator("div:nth-child(7) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").first.fill(agl1)
        page.locator("div:nth-child(7) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").first.press("Enter")

    step("23. CL Layer 1 direction", cl1_dir, page)
    save_html(page, "023_after_CL1_complete")

    # ── 24. CM type ──────────────────────────────────────────────────────────
    def cm_type():
        page.locator("#cloud_med_type_cm div").nth(1).click(timeout=TIMEOUT)
        page.locator("#cloud_med_type_cm").get_by_role("textbox").fill(cm_value)
        page.locator("#cloud_med_type_cm").get_by_role("textbox").press("Enter")

    step("24. CM (medium cloud) type", cm_type, page)

    if cm_value != "0":
        # ── 25. NCM ──────────────────────────────────────────────────────────
        def ncm():
            page.locator("#cloud_med_cover_oktas div").nth(1).click(timeout=TIMEOUT)
            page.locator("#cloud_med_cover_oktas").get_by_role("textbox").fill(ui['ncm_awan_menengah'])
            page.locator("#cloud_med_cover_oktas").get_by_role("textbox").press("Enter")
        step("25. NCM oktas", ncm, page)

        # ── 26. CM layer type ─────────────────────────────────────────────────
        def cm_layer_type():
            page.locator(".col-4 > div:nth-child(3) > .ant-select > .ant-select-selection").first.click(timeout=TIMEOUT)
            page.get_by_role("option", name=cm1_value).click(timeout=TIMEOUT)
        step("26. CM layer type", cm_layer_type, page)

        # ── 27. CM base height ────────────────────────────────────────────────
        def cm_base():
            page.locator("#cloud_med_base_1").click(timeout=TIMEOUT)
            page.locator("#cloud_med_base_1").fill(ui['tinggi_dasar_aw_cm'])
        step("27. CM base height", cm_base, page)

        # ── 28. CM direction ──────────────────────────────────────────────────
        def cm_dir():
            page.locator("div:nth-child(6) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").first.click(timeout=TIMEOUT)
            page.locator("div:nth-child(6) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").first.fill(agcm)
        step("28. CM direction", cm_dir, page)

    save_html(page, "028_after_CM_section")

    # ── 29. CH type ───────────────────────────────────────────────────────────
    def ch_type():
        page.locator("#cloud_high_type_ch div").nth(1).click(timeout=TIMEOUT)
        page.locator("#cloud_high_type_ch").get_by_role("textbox").fill(ch_value)
        page.locator("#cloud_high_type_ch").get_by_role("textbox").press("Enter")

    step("29. CH (high cloud) type", ch_type, page)

    if ch_value != "0":
        # ── 30. NCH ──────────────────────────────────────────────────────────
        def nch():
            page.locator("#cloud_high_cover_oktas div").nth(1).click(timeout=TIMEOUT)
            page.locator("#cloud_high_cover_oktas").get_by_role("textbox").fill(ui['nch_awan_tinggi'])
            page.locator("#cloud_high_cover_oktas div").nth(1).press("Enter")
        step("30. NCH oktas", nch, page)

        # ── 31. CH layer type ─────────────────────────────────────────────────
        def ch_layer_type():
            page.locator("div:nth-child(3) > .card > .card-body > #collapse-row-2 > div > div:nth-child(2) > div:nth-child(3) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").click(timeout=TIMEOUT)
            page.get_by_role("option", name=ch1_value).click(timeout=TIMEOUT)
        step("31. CH layer type", ch_layer_type, page)
        save_html(page, "031_after_CH_type")

        # ── 32. CH jumlah ─────────────────────────────────────────────────────
        def ch_count():
            page.locator("div:nth-child(3) > .card > .card-body > #collapse-row-2 > div > div:nth-child(2) > div:nth-child(4) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").click(timeout=TIMEOUT)
            page.locator("div:nth-child(3) > .card > .card-body > #collapse-row-2 > div > div:nth-child(2) > div:nth-child(4) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").fill(ui['nch_awan_tinggi'])
            page.locator("div:nth-child(3) > .card > .card-body > #collapse-row-2 > div > div:nth-child(2) > div:nth-child(4) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").press("Enter")
        step("32. CH jumlah", ch_count, page)

        # ── 33. CH base height ────────────────────────────────────────────────
        def ch_base():
            page.locator("#cloud_high_base_1").click(timeout=TIMEOUT)
            page.locator("#cloud_high_base_1").fill(ui['tinggi_dasar_aw_ch'])
        step("33. CH base height", ch_base, page)

        # ── 34. CH direction ──────────────────────────────────────────────────
        def ch_dir():
            page.locator("div:nth-child(3) > .card > .card-body > #collapse-row-2 > div > div:nth-child(2) > div:nth-child(6) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").click(timeout=TIMEOUT)
            page.locator("div:nth-child(3) > .card > .card-body > #collapse-row-2 > div > div:nth-child(2) > div:nth-child(6) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").fill(agch)
        step("34. CH direction", ch_dir, page)

    save_html(page, "034_after_CH_section")

    # ── 35. Land condition ────────────────────────────────────────────────────
    def land():
        page.locator("#land_cond div").nth(1).click(timeout=TIMEOUT)
        page.locator("#land_cond").get_by_role("textbox").fill(ui['keadaan_tanah'])
        page.locator("#land_cond").get_by_role("textbox").press("Enter")

    step("35. Land condition", land, page, capture_selector="#land_cond")

    # ── 36. Preview & Generate Sandi ─────────────────────────────────────────
    def preview():
        btn = page.get_by_role("button", name="Preview & Generate Sandi")
        btn.wait_for(state="visible", timeout=TIMEOUT)
        btn.click()
        page.wait_for_timeout(2000)

    step("36. Click 'Preview & Generate Sandi'", preview, page)
    save_html(page, "036_after_preview_click")
    save_screenshot(page, "036_preview_result")

    # ── Final report ──────────────────────────────────────────────────────────
    ctx.close()

    passed = [r for r in results if r['status'] == 'PASS']
    failed = [r for r in results if r['status'] == 'FAIL']

    print(f"\n{'='*60}")
    print(f"  E2E TEST COMPLETE")
    print(f"  Passed: {len(passed)} / {len(results)}")
    print(f"  Failed: {len(failed)} / {len(results)}")
    print(f"  Results saved to: {RESULTS}/")
    print(f"{'='*60}")

    if failed:
        print("\nFAILED STEPS:")
        for r in failed:
            print(f"  [{r['step']:03d}] {r['label']}")
            lines = r['error'].strip().splitlines()
            print(f"       {lines[-1]}")
            if r['html']:
                print(f"       HTML: {r['html']}")

    # Save JSON summary
    summary = {
        "run_at": datetime.now().isoformat(),
        "total": len(results),
        "passed": len(passed),
        "failed": len(failed),
        "steps": results,
    }
    (RESULTS / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    print(f"\nFull summary: {RESULTS / 'summary.json'}")
