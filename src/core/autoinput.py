import re
import time
from datetime import datetime, timezone, date as _date
from ..utils import get_logger

logger = get_logger(__name__)


def _select_calendar_date(page, target: _date, timeout: int = 15000) -> None:
    """
    Select a specific date in the Bootstrap-Vue BFormDatepicker widget used by BMKG.

    Calendar structure (lang=id):
      - Current-month days: <div role="button" data-date="YYYY-MM-DD" aria-label="D/M/YYYY">
        (no aria-hidden attribute — fully clickable)
      - Overflow days from adjacent months: same but with aria-hidden="true"
        (must navigate away rather than clicking these)

    Strategy:
      1. Open the calendar (caller's responsibility — the #input-datepicker__value_ click).
      2. Check if the target date is visible and NOT hidden.
      3. If not, click "Previous month" or "Next month" navigation and repeat.
      4. Click the target date cell.
    """
    target_str = target.strftime("%Y-%m-%d")

    for attempt in range(14):   # safety cap — 14 months navigation max
        # A date cell is "selectable" when it has no aria-hidden="true"
        target_sel  = f'[data-date="{target_str}"]:not([aria-hidden="true"])'
        target_el   = page.locator(target_sel)

        if target_el.count() > 0:
            target_el.first.click(timeout=timeout)
            logger.info(f"Date selected: {target_str}")
            return

        # Determine which direction to navigate.
        # Read any visible (non-hidden) date cell to know which month is shown.
        visible_cell = page.locator('[data-date]:not([aria-hidden="true"])').first
        if visible_cell.count() == 0:
            # Fallback: read any cell with data-date to get current month
            any_cell = page.locator('[data-date]').first
            if any_cell.count() == 0:
                raise RuntimeError("No calendar cells found — calendar may not be open.")
            shown_str = any_cell.get_attribute("data-date") or ""
        else:
            shown_str = visible_cell.get_attribute("data-date") or ""

        try:
            shown = _date.fromisoformat(shown_str)
        except ValueError:
            raise RuntimeError(f"Cannot parse shown calendar date: {shown_str!r}")

        if target < shown:
            page.locator('button[aria-label="Previous month"]').click(timeout=timeout)
        else:
            btn = page.locator('button[aria-label="Next month"]')
            if btn.get_attribute("aria-disabled") == "true":
                raise RuntimeError(f"Cannot navigate forward — next month button disabled. Target: {target_str}")
            btn.click(timeout=timeout)

        page.wait_for_timeout(300)

    raise RuntimeError(f"Could not navigate to {target_str} after 14 month steps.")


def _select_antd(page, container_selector: str, value: str, timeout: int = 15000) -> None:
    """
    Select a value in an Ant Design v3 Select/Combobox.

    Handles both searchable and non-searchable components:
      - Searchable  : after clicking, the GLOBALLY OPEN dropdown shows a text input.
                      We fill it and Enter — only one option appears.
      - Non-searchable: no text input; we click the matching option from the list.

    Uses the globally-open dropdown (.ant-select-dropdown without display:none) rather
    than scoping to the container, because positional selectors like
    "div:nth-child(4) > .ant-select" are evaluated page-wide and .first may pick the
    wrong element. There can only be ONE open Ant Design dropdown at a time.

    Args:
        container_selector: CSS selector for the .ant-select container
                            (e.g. "#wind_indicator_iw" or "div:nth-child(4) > .ant-select").
        value:              Code number ("5") or partial text to select.
    """
    # Click the .ant-select-selection to open the dropdown
    selection = page.locator(f"{container_selector} .ant-select-selection")
    selection.first.click(timeout=timeout)
    page.wait_for_timeout(400)

    # Find the search input of the ONE open Ant Design dropdown.
    # There can only be one open dropdown at a time so a global selector is reliable.
    open_search = page.locator(
        '.ant-select-dropdown:not([style*="display: none"]) .ant-select-search__field'
    )

    if open_search.count() > 0 and open_search.first.is_visible():
        # Searchable: type the value — the dropdown filters to one match.
        open_search.first.fill(value)
        # Press Enter on the OUTER .ant-select-selection div (not the search input).
        # Ant Design v3 requires Enter on the selection container to confirm.
        selection.first.press("Enter")
    else:
        # Non-searchable: click the matching option from the visible list
        page.get_by_role("option", name=re.compile(
            rf"^{re.escape(value)}\b", re.IGNORECASE
        )).first.click(timeout=timeout)


class AutoInput:
    def __init__(self, page, user_input, obs, ww, w1w2, awan_lapisan, arah_angin, ci, cm, ch):
        """
        Inisialisasi objek AutoInput.

        Args:
            page: Objek halaman Playwright yang sedang aktif.
            user_input: Dictionary berisi input data dari pengguna.
            obs, ww, w1w2, awan_lapisan, arah_angin, ci, cm, ch: Mapping untuk pengisian data cuaca.
        """
        self.page = page
        self.user_input = user_input
        self.obs = obs
        self.ww = ww
        self.w1w2 = w1w2
        self.awan_lapisan = awan_lapisan
        self.arah_angin = arah_angin
        self.ci = ci
        self.cm = cm
        self.ch = ch

    def input_cloud_layer_2(self):
        """Mengisi data untuk lapisan awan kedua (CL Lapisan 2) berdasarkan user_input."""
        page = self.page

        # 25 Activate switch for the second cloud layer
        page.wait_for_selector(".switch-icon-right > .feather", timeout=60000)
        page.locator(".switch-icon-right > .feather").first.click(timeout=30000)

        CL_COL = "#collapse-row-2 .col-3"

        # 26 Jenis CL Lapisan 2 — layer 2 rows are nth-child(3) deeper (sub-row)
        jenis_cl_lap2_value = self.awan_lapisan.get(self.user_input['jenis_cl_lapisan2'], "0")
        page.locator(f"{CL_COL} > div:nth-child(3) > div:nth-child(3) > .ant-select > .ant-select-selection").first.click()
        page.wait_for_timeout(300)
        page.get_by_role("option", name=re.compile(
            re.escape(jenis_cl_lap2_value), re.IGNORECASE
        )).first.click()

        # 27 Jumlah CL Lapisan 2
        _select_antd(page, f"{CL_COL} > div:nth-child(3) > div:nth-child(4) > .ant-select", self.user_input['jumlah_cl_lapisan2'])

        # 28 Tinggi Dasar Awan Lapisan 2
        page.locator("#cloud_low_base_2").click()
        page.locator("#cloud_low_base_2").fill(self.user_input['tinggi_dasar_aw_lapisan2'])

        # 29 Arah Gerak Awan Lapisan 2
        arah_gerak_aw_lap2_value = self.arah_angin.get(self.user_input['arah_gerak_aw_lapisan2'], "0")
        _select_antd(page, f"{CL_COL} > div:nth-child(3) > div:nth-child(7) > .ant-select", arah_gerak_aw_lap2_value)

    def fill_form(self, preview=True):
        """Mengisi seluruh form berdasarkan input pengguna, termasuk logika pengisian berdasarkan jam pengamatan.

        Args:
            preview: Jika True, klik tombol Preview setelah form terisi. Set False untuk auto-submit.
        """

        try:
            page = self.page
            user_input = self.user_input

            print("Memulai Proses Input Data...")

            # Pilih stasiun
            page.locator("#select-station div").nth(1).click()
            page.get_by_role("option", name=re.compile(r"^Stasiun")).click()

            # Tanggal Pengamatan — open calendar, navigate if needed, click target day.
            # Uses _select_calendar_date() which handles same-month and cross-month cases.
            input_date_str = user_input.get('tanggal_pengamatan')
            if input_date_str:
                try:
                    target_date = _date.fromisoformat(input_date_str)  # expects YYYY-MM-DD
                except ValueError:
                    target_date = _date.today()
                    logger.warning(f"Invalid tanggal_pengamatan '{input_date_str}', defaulting to today")
            else:
                target_date = _date.today()

            page.locator("#input-datepicker__value_").click()
            # Wait for the calendar dialog to actually open before looking for date cells
            page.wait_for_selector(".b-calendar-grid-body, [data-date]", timeout=10000)
            _select_calendar_date(page, target_date)

            # 1 Jam Pengamatan
            page.locator("#input-jam div").nth(1).click()
            page.locator("#input-jam").get_by_role("textbox").fill(user_input['jam_pengamatan'])
            page.locator("#input-jam").get_by_role("textbox").press("Enter")
            page.wait_for_load_state("networkidle")

            # Handle SweetAlert2 dialogs that appear after hour selection.
            #
            # Case A — "Data Tersedia": this hour already has submitted data.
            #   Confirm button text: "Lihat" → click it to load existing data
            #   into the form (edit mode). All fields can then be overwritten.
            #   The submit chain must use "Send & Update" instead of "Send".
            #
            # Case B — blocking warning: a prior hour has no data yet.
            #   The site prevents skipping hours. The alert will say something
            #   like "Data jam sebelumnya belum ada". Clicking OK acknowledges
            #   it but the form will not be usable for this hour.
            #
            # Case C — any other confirmation (OK button only): dismiss it.
            page.wait_for_timeout(800)
            swal = page.locator(".swal2-popup")
            if swal.count() > 0 and swal.first.is_visible():
                title_text   = page.locator("#swal2-title").text_content() or ""
                content_text = page.locator("#swal2-content").text_content() or ""
                confirm_btn  = page.locator(".swal2-confirm")
                confirm_text = confirm_btn.first.text_content() or ""
                logger.info(f"SweetAlert2 dialog: title={title_text!r} content={content_text!r}")

                if "belum" in content_text.lower() or "belum" in title_text.lower():
                    # Blocking: prior hour is missing — dismiss and raise so caller knows
                    confirm_btn.first.click()
                    raise RuntimeError(
                        f"Cannot fill hour {user_input['jam_pengamatan']}: "
                        f"a previous observation hour has no data yet. ({content_text.strip()})"
                    )
                else:
                    # "Data Tersedia" or any other dialog — click the confirm/OK button
                    confirm_btn.first.click()
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(500)
                    logger.info(f"SweetAlert2 dismissed (confirm='{confirm_text}')")

            # Observer — selected AFTER hour because the dropdown only becomes
            # populated/enabled once the form fully loads with the chosen hour.
            obs_el    = page.locator("#select-observer")
            obs_class = obs_el.get_attribute("class") or ""
            logger.info(f"Observer class after hour selection: {obs_class!r}")

            if "ant-select-disabled" not in obs_class:
                obs_key  = user_input.get('obs_onduty', '').lower()
                obs_name = self.obs.get(obs_key, "")
                logger.info(f"Observer enabled — selecting: {obs_name!r} (key={obs_key!r})")
                page.locator("#select-observer div").nth(1).click()
                page.wait_for_timeout(400)
                exact = page.get_by_role("option", name=obs_name)
                if obs_name and exact.count() > 0:
                    exact.first.click()
                    logger.info(f"Observer selected (exact): {obs_name!r}")
                else:
                    first_token = obs_name.split()[0] if obs_name else obs_key
                    partial = page.get_by_role("option", name=re.compile(
                        re.escape(first_token), re.IGNORECASE
                    ))
                    if partial.count() > 0:
                        chosen = partial.first.text_content() or ""
                        partial.first.click()
                        logger.warning(f"Observer partial match used: {chosen!r}")
                    else:
                        all_opts = page.get_by_role("option").all_text_contents()
                        logger.error(f"Observer '{obs_name}' not found. Options: {all_opts}")
                        page.keyboard.press("Escape")
            else:
                logger.info("Observer auto-populated from session, skipping")

            # conditional pengisian parameter tertentu pada jam-jam penting
            jam_penting = int(user_input['jam_pengamatan'])

            if jam_penting == 0:
                # 14 Suhu Minimum — use stable field ID confirmed from HTML
                page.locator("#temp_min_c_tntntn").click()
                page.locator("#temp_min_c_tntntn").fill(user_input['suhu_minimum'])

                # 16 Hujan Ditakar
                try:
                    hujan_ditakar = f"{float(user_input['hujan_ditakar']):.1f}"
                except (ValueError, TypeError):
                    hujan_ditakar = "0.0"
                page.locator("#rainfall_last_mm").click()
                page.locator("#rainfall_last_mm").fill(hujan_ditakar)

                # 42 Penguapan - Format to one decimal place
                try:
                    penguapan = f"{float(user_input['penguapan']):.1f}"
                except (ValueError, TypeError):
                    penguapan = "0.0"
                page.get_by_label("Penguapan (mm)").click()
                page.get_by_label("Penguapan (mm)").fill(penguapan)

                # 43 Pengenal Data Penguapan (IE)
                page.locator("#evaporation_eq_indicator_ie").get_by_role("combobox").click()
                page.locator("#evaporation_eq_indicator_ie").get_by_role("textbox").fill(user_input['pengenal_penguapan'])

                # 44 Lama Penyinaran Matahari - Format to one decimal place
                try:
                    lama_penyinaran = f"{float(user_input['lama_penyinaran']):.1f}"
                except (ValueError, TypeError):
                    lama_penyinaran = "0.0"
                page.get_by_label("Lama Penyinaran Matahari (jam)").click()
                page.get_by_label("Lama Penyinaran Matahari (jam)").fill(lama_penyinaran)

            elif jam_penting == 12:
                # 13 Suhu Maksimum — use stable field ID
                page.locator("#temp_max_c_txtxtx").click()
                page.locator("#temp_max_c_txtxtx").fill(user_input['suhu_maksimum'])

                # 16 Hujan Ditakar
                try:
                    hujan_ditakar = f"{float(user_input['hujan_ditakar']):.1f}"
                except (ValueError, TypeError):
                    hujan_ditakar = "0.0"
                page.locator("#rainfall_last_mm").click()
                page.locator("#rainfall_last_mm").fill(hujan_ditakar)

            elif jam_penting in [3, 6, 9, 15, 18, 21]:
                # 16 Hujan Ditakar
                try:
                    hujan_ditakar = f"{float(user_input['hujan_ditakar']):.1f}"
                except (ValueError, TypeError):
                    hujan_ditakar = "0.0"
                page.locator("#rainfall_last_mm").click()
                page.locator("#rainfall_last_mm").fill(hujan_ditakar)

            else:
                print("Jam Pengamatan Tidak Termasuk Jam Pengiriman Utama.")

            # 2 Pengenal data Angin (iw)
            page.locator("#wind_indicator_iw div").nth(1).click()
            page.locator("#wind_indicator_iw").get_by_role("textbox").fill(user_input['pengenal_angin'])
            page.locator("#wind_indicator_iw").get_by_role("textbox").press("Enter")

            # 3 Arah Angin
            page.get_by_label("Arah Angin (derajat)").click()
            page.get_by_label("Arah Angin (derajat)").fill(user_input['arah_angin'])

            # 4 Kecepatan Angin
            page.get_by_label("Kecepatan Angin (knot)").click()
            page.get_by_label("Kecepatan Angin (knot)").fill(user_input['kecepatan_angin'])

            # 5 Jarak Penglihatan (Visibility)
            page.get_by_label("Jarak penglihatan mendatar (").click()
            page.get_by_label("Jarak penglihatan mendatar (").fill(user_input['jarak_penglihatan'])

            # 6 Cuaca Saat Pengamatan (ww)
            ww_value = self.ww.get(user_input['cuaca_pengamatan'], "00")
            page.locator("#present_weather_ww div").nth(1).click()
            page.locator("#present_weather_ww").get_by_role("textbox").fill(ww_value)
            page.locator("#present_weather_ww").get_by_role("textbox").press("Enter")

            # 7 Cuaca yang lalu (W1)
            w1_value = self.w1w2.get(user_input['cuaca_w1'], "0")
            page.locator("#past_weather_w1 div").nth(1).click()
            page.locator("#past_weather_w1").get_by_role("textbox").fill(w1_value)
            page.locator("#past_weather_w1").get_by_role("textbox").press("Enter")

            # 8 Cuaca yang lalu (W2)
            w2_value = self.w1w2.get(user_input['cuaca_w2'], "0")
            page.locator("#past_weather_w2 div").nth(1).click()
            page.locator("#past_weather_w2").get_by_role("textbox").fill(w2_value)
            page.locator("#past_weather_w2").get_by_role("textbox").press("Enter")

            # NOTE: #input-cuaca-ix (Pengenal Data Cuaca ix) is auto-calculated
            # by the site and is disabled — do not attempt to fill it.

            # 9 Tekanan QFF
            page.get_by_label("Tekanan QFF").click()
            page.get_by_label("Tekanan QFF").fill(user_input['tekanan_qff'])

            # 10 Tekanan QFE
            page.get_by_label("Tekanan QFE").click()
            page.get_by_label("Tekanan QFE").fill(user_input['tekanan_qfe'])

            # 11 Suhu Bola Kering
            page.get_by_label("Suhu Bola Kering (℃)").click()
            page.get_by_label("Suhu Bola Kering (℃)").fill(user_input['suhu_bola_kering'])

            # 12 Suhu Bola Basah
            page.get_by_label("Suhu Bola Basah (℃)").click()
            page.get_by_label("Suhu Bola Basah (℃)").fill(user_input['suhu_bola_basah'])

            # 15 Bagian Langit Tertutup Awan (oktas)
            page.locator("#cloud_cover_oktas_m div").nth(1).click()
            page.locator("#cloud_cover_oktas_m").get_by_role("textbox").fill(user_input['oktas'])
            page.locator("#cloud_cover_oktas_m").get_by_role("textbox").press("Enter")

            # 17 CL Dominan — use _select_antd which handles both searchable
            # and non-searchable selects via the globally-open dropdown
            cl_value = self.ci.get(user_input['cl_dominan'], "0")
            _select_antd(page, "#cloud_low_type_cl", cl_value)

            # CL section is inside #collapse-row-2 .col-3
            # Scoping all CL layer selectors to this container prevents accidentally
            # targeting the observer dropdown (which also sits in a div:nth-child(3)
            # in the header section).
            CL_COL = "#collapse-row-2 .col-3"

            if cl_value != "0":
                # 18 NCL Total (Jumlah Awan Rendah)
                _select_antd(page, "#cloud_low_cover_oktas", user_input['ncl_total'])

                # 19 Jenis CL Lapisan 1 — nth-child(3) row inside .col-3
                jenis_cl_lap1_value = self.awan_lapisan.get(user_input['jenis_cl_lapisan1'], "8")
                page.locator(f"{CL_COL} > div:nth-child(3) > .ant-select > .ant-select-selection").first.click()
                page.wait_for_timeout(300)
                page.get_by_role("option", name=re.compile(
                    re.escape(jenis_cl_lap1_value), re.IGNORECASE
                )).first.click()

                # 20 Jumlah CL Lapisan 1 — nth-child(4) row inside .col-3
                _select_antd(page, f"{CL_COL} > div:nth-child(4) > .ant-select", user_input['jumlah_cl_lapisan1'])

                # 21 Tinggi Dasar Awan Lapisan 1
                page.locator("#cloud_low_base_1").click()
                page.locator("#cloud_low_base_1").fill(user_input['tinggi_dasar_aw_lapisan1'])

                # 23 Arah Gerak Awan Lapisan 1 — nth-child(7) row inside .col-3
                arah_gerak_aw_lap1_value = self.arah_angin.get(user_input['arah_gerak_aw_lapisan1'], "0")
                _select_antd(page, f"{CL_COL} > div:nth-child(7) > .ant-select", arah_gerak_aw_lap1_value)

                # Conditional untuk membuka pengisian tinggi puncak, sudut elevasi awan, dan awan lapisan ke-2
                if user_input['jenis_cl_lapisan1'] in ["CU", "CB"]:
                    has_peak = user_input.get('tinggi_puncak_aw_lapisan1', '')
                    if has_peak and has_peak not in ("0", ""):
                        # 22 Tinggi Puncak Awan Lapisan 1
                        page.locator("#cloud_low_peak_1").click()
                        page.locator("#cloud_low_peak_1").fill(has_peak)

                        # 24 Sudut Elevasi Awan Lapisan 1
                        page.locator("#cloud_elevation_1_angle_ec div").nth(1).click()
                        page.locator("#cloud_elevation_1_angle_ec").get_by_role("textbox").fill(
                            str(user_input['sudut_elevasi_aw_lapisan1']))
                        page.locator("#cloud_elevation_1_angle_ec").get_by_role("textbox").press("Enter")

                        # Arah sebenarnya — nth-child(9) row inside .col-3
                        _select_antd(page, f"{CL_COL} > div:nth-child(9) > .ant-select", arah_gerak_aw_lap1_value)

                        if user_input['jenis_cl_lapisan1'] == "CB":
                            self.input_cloud_layer_2()

            # 30 CM Awan Menengah
            cm_value = self.cm.get(user_input['cm_awan_menengah'], "0")
            page.locator("#cloud_med_type_cm div").nth(1).click()
            page.locator("#cloud_med_type_cm").get_by_role("textbox").fill(cm_value)
            page.locator("#cloud_med_type_cm").get_by_role("textbox").press("Enter")

            # Conditional: jika jenis_awan_menengah_value == "0", lewati bagian berikut
            if cm_value != "0":
                # 31 NCM Jumlah Awan menengah
                page.locator("#cloud_med_cover_oktas div").nth(1).click()
                page.locator("#cloud_med_cover_oktas").get_by_role("textbox").fill(user_input['ncm_awan_menengah'])
                page.locator("#cloud_med_cover_oktas").get_by_role("textbox").press("Enter")

                # 32 Jenis Awan Menengah
                jenis_awan_menengah_value = self.awan_lapisan.get(user_input['jenis_awan_menengah'], "3")
                page.locator(".col-4 > div:nth-child(3) > .ant-select > .ant-select-selection").first.click()
                page.wait_for_timeout(300)
                page.get_by_role("option", name=re.compile(
                    re.escape(jenis_awan_menengah_value), re.IGNORECASE
                )).first.click()

                # 33 Jumlah awan menengah — type count, one option appears
                _select_antd(page, ".col-4 > div:nth-child(4) > .ant-select", user_input['ncm_awan_menengah'])

                # 34 Tinggi Dasar Awan Menengah
                page.locator("#cloud_med_base_1").click()
                page.locator("#cloud_med_base_1").fill(user_input['tinggi_dasar_aw_cm'])

                # 35 Arah Gerak Awan CM
                arah_gerak_cm_value = self.arah_angin.get(user_input['arah_gerak_cm'], "0")
                _select_antd(page, "div:nth-child(6) > .ant-select", arah_gerak_cm_value)

            # 36 CH Awan Tinggi
            ch_value = self.ch.get(user_input['ch_awan_tinggi'], "0")
            page.locator("#cloud_high_type_ch div").nth(1).click()
            page.locator("#cloud_high_type_ch").get_by_role("textbox").fill(ch_value)
            page.locator("#cloud_high_type_ch").get_by_role("textbox").press("Enter")

            if ch_value != "0":
                # 37 NCH jumah awan tinggi
                page.locator("#cloud_high_cover_oktas div").nth(1).click()
                page.locator("#cloud_high_cover_oktas").get_by_role("textbox").fill(user_input['nch_awan_tinggi'])
                # page.get_by_role("option", name="oktas").click()
                page.locator("#cloud_high_cover_oktas div").nth(1).press("Enter")

                # 38 Jenis awan tinggi
                CH_BASE = "div:nth-child(3) > .card > .card-body > #collapse-row-2 > div > div:nth-child(2)"
                jenis_awan_tinggi_value = self.awan_lapisan.get(user_input['ch_awan_tinggi'], "0")
                page.locator(f"{CH_BASE} > div:nth-child(3) > .ant-select > .ant-select-selection").click()
                page.wait_for_timeout(300)
                page.get_by_role("option", name=re.compile(
                    re.escape(jenis_awan_tinggi_value), re.IGNORECASE
                )).first.click()

                # 39 Jumlah awan tinggi — type count, one option appears
                _select_antd(page, f"{CH_BASE} > div:nth-child(4) > .ant-select", user_input['nch_awan_tinggi'])

                # 40 Tinggi Dasar Awan Tinggi
                page.locator("#cloud_high_base_1").click()
                page.locator("#cloud_high_base_1").fill(user_input['tinggi_dasar_aw_ch'])

                # 41 Arah Gerak Awan CH
                arah_gerak_ch_value = self.arah_angin.get(user_input['arah_gerak_ch'], "0")
                _select_antd(page, f"{CH_BASE} > div:nth-child(6) > .ant-select", arah_gerak_ch_value)

            # 45 Keadaan Tanah
            page.locator("#land_cond div").nth(1).click()
            page.locator("#land_cond").get_by_role("textbox").fill(user_input['keadaan_tanah'])
            page.locator("#land_cond").get_by_role("textbox").press("Enter")

            if preview:
                time.sleep(1)
                page.get_by_role("button", name="Preview & Generate Sandi").click()

            logger.info("Proses pengisian form selesai.")

        except Exception as e:
            logger.error(f"Terdapat error pada: {e}")
            raise
