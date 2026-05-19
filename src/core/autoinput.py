import re
import time
from datetime import datetime, timezone
from ..utils import get_logger

logger = get_logger(__name__)

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

        # 26 Jenis CL Lapisan 2
        jenis_cl_lap2_value = self.awan_lapisan.get(self.user_input['jenis_cl_lapisan2'], "0")
        page.locator("div:nth-child(3) > div:nth-child(3) > .ant-select > .ant-select-selection").first.click()
        page.get_by_role("option", name=jenis_cl_lap2_value).click()

        # 27 Jumlah CL Lapisan 2
        page.locator(
            "div:nth-child(3) > div:nth-child(4) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").first.click()
        page.locator(
            "div:nth-child(3) > div:nth-child(4) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").first.fill(
            self.user_input['jumlah_cl_lapisan2'])
        page.get_by_role("option", name="oktas").click()

        # 28 Tinggi Dasar Awan Lapisan 2
        page.locator("#cloud_low_base_2").click()
        page.locator("#cloud_low_base_2").fill(self.user_input['tinggi_dasar_aw_lapisan2'])

        # 29 Arah Gerak Awan Lapisan 2
        arah_gerak_aw_lap2_value = self.arah_angin.get(self.user_input['arah_gerak_aw_lapisan2'], "0")
        page.locator(
            "div:nth-child(3) > div:nth-child(7) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").click()
        page.locator(
            "div:nth-child(3) > div:nth-child(7) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").fill(arah_gerak_aw_lap2_value)
        page.locator(
            "div:nth-child(3) > div:nth-child(7) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").press(
            "Enter")

    def fill_form(self):
        """Mengisi seluruh form berdasarkan input pengguna, termasuk logika pengisian berdasarkan jam pengamatan."""

        try:
            page = self.page
            user_input = self.user_input

            print("Memulai Proses Input Data...")

            # Pilih stasiun
            page.locator("#select-station div").nth(1).click()
            page.get_by_role("option", name=re.compile(r"^Stasiun")).click()

            # pilih observer on duty
            obs_onduty_value = self.obs.get(user_input['obs_onduty'].lower(), "Zulkifli Ramadhan")
            page.locator("#select-observer div").nth(1).click()
            page.get_by_role("option", name=obs_onduty_value).click()

            # Tanggal Pengamatan
            today = datetime.now(timezone.utc)
            input_date = user_input.get('tanggal_pengamatan')
            
            if input_date:
                # If specific date is provided, use it (format: DD/MM)
                page.locator("#input-datepicker__value_").click()
                page.get_by_label(f"{input_date}/").click()
            else:
                # Use today's date as default
                tgl_harini = f"/{today.month}/{today.year} (Today)"
                page.locator("#input-datepicker__value_").click()
                page.get_by_label(tgl_harini).click()

            # 1 Jam Pengamatan
            page.locator("#input-jam div").nth(1).click()
            page.locator("#input-jam").get_by_role("textbox").fill(user_input['jam_pengamatan'])
            page.locator("#input-jam").get_by_role("textbox").press("Enter")
            page.wait_for_load_state("networkidle")

            # conditional pengisian parameter tertentu pada jam-jam penting
            jam_penting = int(user_input['jam_pengamatan'])

            if jam_penting == 0:
                # 14 Suhu Minimum
                page.get_by_label("Suhu Minimum (℃)").click()
                page.get_by_label("Suhu Minimum (℃)").fill(user_input['suhu_minimum'])

                # 16 Hujan Ditakar - Format to one decimal place
                try:
                    hujan_ditakar = f"{float(user_input['hujan_ditakar']):.1f}"
                except (ValueError, TypeError):
                    hujan_ditakar = "0.0"
                page.get_by_label("Hujan takaran terakhir (mm)").click()
                page.get_by_label("Hujan takaran terakhir (mm)").fill(hujan_ditakar)

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
                # 13 Suhu Maksimum
                page.get_by_label("Suhu Maksimum (℃)").click()
                page.get_by_label("Suhu Maksimum (℃)").fill(user_input['suhu_maksimum'])

                # 16 Hujan Ditakar - Format to one decimal place
                try:
                    hujan_ditakar = f"{float(user_input['hujan_ditakar']):.1f}"
                except (ValueError, TypeError):
                    hujan_ditakar = "0.0"
                page.get_by_label("Hujan takaran terakhir (mm)").click()
                page.get_by_label("Hujan takaran terakhir (mm)").fill(hujan_ditakar)

            elif jam_penting in [3, 6, 9, 15, 18, 21]:
                # 16 Hujan Ditakar - Format to one decimal place
                try:
                    hujan_ditakar = f"{float(user_input['hujan_ditakar']):.1f}"
                except (ValueError, TypeError):
                    hujan_ditakar = "0.0"
                page.get_by_label("Hujan takaran terakhir (mm)").click()
                page.get_by_label("Hujan takaran terakhir (mm)").fill(hujan_ditakar)

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

            # 17 CL Dominan
            cl_value = self.ci.get(user_input['cl_dominan'], "0")
            page.locator("#cloud_low_type_cl div").nth(1).click()
            if cl_value == "1":
                page.get_by_role("option", name="1 - cumulus humilis atau").click()
            else:
                page.locator("#cloud_low_type_cl").get_by_role("textbox").fill(cl_value)
                page.locator("#cloud_low_type_cl").get_by_role("textbox").press("Enter")

            if cl_value != "0":
                # 18 NCL Total (Jumlah Awan Rendah)
                page.locator("#cloud_low_cover_oktas div").nth(1).click()
                page.locator("#cloud_low_cover_oktas").get_by_role("textbox").fill(user_input['ncl_total'])
                page.locator("#cloud_low_cover_oktas").get_by_role("textbox").press("Enter")

                # 19 Jenis CL Lapisan 1
                jenis_cl_lap1_value = self.awan_lapisan.get(user_input['jenis_cl_lapisan1'], "8")
                page.locator("div:nth-child(3) > .ant-select > .ant-select-selection").first.click()
                page.get_by_role("option", name=jenis_cl_lap1_value).click()

                # 20 Jumlah CL Lapisan 1
                page.locator("div:nth-child(4) > .ant-select > .ant-select-selection").first.click()
                page.locator("div:nth-child(4) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").first.fill(user_input['jumlah_cl_lapisan1'])
                # page.get_by_role("option", name="oktas").click()
                page.locator("div:nth-child(4) > .ant-select > .ant-select-selection").first.press("Enter")

                # 21 Tinggi Dasar Awan Lapisan 1
                page.locator("#cloud_low_base_1").click()
                page.locator("#cloud_low_base_1").fill(user_input['tinggi_dasar_aw_lapisan1'])

                # 23 Arah Gerak Awan Lapisan 1
                arah_gerak_aw_lap1_value = self.arah_angin.get(user_input['arah_gerak_aw_lapisan1'], "0")
                page.locator("div:nth-child(7) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").first.click()
                page.locator("div:nth-child(7) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").first.fill(arah_gerak_aw_lap1_value)

                # Condtional untuk membuka pengisian tinggi puncak, sudut elevasi awan, dan awan lapisan ke-2
                if user_input['jenis_cl_lapisan1'] in ["CU", "CB"]:
                    has_peak = user_input['tinggi_puncak_aw_lapisan1']
                    if has_peak != "0":
                        # 22 Tinggi Puncak Awan Lapisan 1
                        page.locator("#cloud_low_peak_1").click()
                        page.locator("#cloud_low_peak_1").fill(has_peak)

                        # 24 Sudut Elevasi Awan Lapisan 1
                        page.locator("#cloud_elevation_1_angle_ec div").nth(1).click()
                        page.locator("#cloud_elevation_1_angle_ec").get_by_role("textbox").fill(
                            str(user_input['sudut_elevasi_aw_lapisan1']))
                        page.locator("#cloud_elevation_1_angle_ec").get_by_role("textbox").press("Enter")

                        # bagian kolom arah sebenarnya >>>> di samain aja nilainya seperi arah Arah Gerak Awan Lapisan 1
                        page.locator("div:nth-child(9) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").first.click()
                        page.locator("div:nth-child(9) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").first.fill(arah_gerak_aw_lap1_value)
                        page.locator("div:nth-child(9) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").first.press("Enter")

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
                page.get_by_role("option", name=jenis_awan_menengah_value).click()

                # 33 Jumlah awan menengah
                jumlah_awan_menengah = user_input['ncm_awan_menengah']
                page.locator(".col-4 > div:nth-child(4) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").first.click()
                page.locator(".col-4 > div:nth-child(4) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").first.fill(jumlah_awan_menengah)
                page.locator(".col-4 > div:nth-child(4) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").first.press("Enter")

                # 34  Tinggi Dasar Awan Menengah
                page.locator("#cloud_med_base_1").click()
                page.locator("#cloud_med_base_1").fill(user_input['tinggi_dasar_aw_cm'])

                # 35 Arah Gerak Awan CM
                arah_gerak_cm_value = self.arah_angin.get(user_input['arah_gerak_cm'], "0")
                page.locator("div:nth-child(6) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").first.click()
                page.locator("div:nth-child(6) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").first.fill(arah_gerak_cm_value)

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

                # 38 jenis awan tinggi
                jenis_awan_tinggi_value = self.awan_lapisan.get(user_input['ch_awan_tinggi'], "0")
                page.locator("div:nth-child(3) > .card > .card-body > #collapse-row-2 > div > div:nth-child(2) > div:nth-child(3) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").click()
                page.get_by_role("option", name=jenis_awan_tinggi_value).click()

                # # 39 Jumlah awan tinggi
                jumlah_awan_tinggi = user_input['nch_awan_tinggi']
                page.locator("div:nth-child(3) > .card > .card-body > #collapse-row-2 > div > div:nth-child(2) > div:nth-child(4) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").click()
                page.locator("div:nth-child(3) > .card > .card-body > #collapse-row-2 > div > div:nth-child(2) > div:nth-child(4) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").fill(jumlah_awan_tinggi)
                # page.get_by_role("option", name=f"- {jumlah_awan_tinggi} oktas").click()
                page.locator("div:nth-child(3) > .card > .card-body > #collapse-row-2 > div > div:nth-child(2) > div:nth-child(4) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").press("Enter")

                # 40 Tinggi Dasar Awan Tinggi
                page.locator("#cloud_high_base_1").click()
                page.locator("#cloud_high_base_1").fill(user_input['tinggi_dasar_aw_ch'])

                # 41 Arah Gerak Awan CH
                arah_gerak_ch_value = self.arah_angin.get(user_input['arah_gerak_ch'], "0")
                page.locator("div:nth-child(3) > .card > .card-body > #collapse-row-2 > div > div:nth-child(2) > div:nth-child(6) > .ant-select > .ant-select-selection > .ant-select-selection__rendered").click()
                page.locator("div:nth-child(3) > .card > .card-body > #collapse-row-2 > div > div:nth-child(2) > div:nth-child(6) > .ant-select > .ant-select-selection > .ant-select-selection__rendered > .ant-select-search > .ant-select-search__field__wrap > .ant-select-search__field").fill(arah_gerak_ch_value)

            # 45 Keadaan Tanah
            page.locator("#land_cond div").nth(1).click()
            page.locator("#land_cond").get_by_role("textbox").fill(user_input['keadaan_tanah'])
            page.locator("#land_cond").get_by_role("textbox").press("Enter")

            # Preview
            time.sleep(1)
            page.get_by_role("button", name="Preview").click()

            print("Proses Selesai.")

        except Exception as e:
            print(f"Terdapat error pada: {e}")
