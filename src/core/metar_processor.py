"""
METAR processing functionality for BMKG Auto Input.
"""
import logging
import time
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from ..data.sandi import STATION_CODE, DEFAULT_OBSERVER, obs

logger = logging.getLogger(__name__)

class MetarProcessor:
    """Handles METAR code processing and form filling."""
    
    def __init__(self, page, station_code=None, observer=None, obs_onduty=None):
        """Initialize the METAR processor.

        Args:
            page: Playwright page object
            station_code: ICAO/WMO station code (overrides STATION_CODE from config)
            observer: Full observer name (overrides DEFAULT_OBSERVER from config)
            obs_onduty: Observer short key from sandi.obs dict (e.g. 'titis')
        """
        self.page = page
        self.bmkg_url = "https://bmkgsatu.bmkg.go.id/meteorologi/metarspeci"
        self.input_delay = 0.2
        self.station_code = station_code or STATION_CODE
        # Resolve observer: short key → full name, then fall back to passed name or default
        if obs_onduty:
            self.observer = obs.get(obs_onduty.lower(), DEFAULT_OBSERVER)
        else:
            self.observer = observer or DEFAULT_OBSERVER

    def wait_between_inputs(self):
        """Add a small delay between form inputs."""
        time.sleep(self.input_delay)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(PlaywrightTimeoutError)
    )
    def ensure_page_loaded(self):
        """Ensure the BMKG METAR/SPECI page is loaded before proceeding."""
        try:
            current_url = self.page.url
            if current_url != self.bmkg_url:
                logger.info(f"Redirecting to BMKG METAR/SPECI page: {self.bmkg_url}")
                self.page.goto(self.bmkg_url)
                self.page.wait_for_load_state("networkidle", timeout=30000)
                time.sleep(2)  # Give extra time for the page to stabilize
            logger.info("BMKG METAR/SPECI page loaded successfully")
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout loading BMKG page: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading BMKG page: {e}")
            raise

    def handle_timeout_error(self, error_message: str):
        """Handle timeout errors gracefully.
        
        Args:
            error_message: The error message from the timeout
        """
        logger.warning(f"Timeout occurred: {error_message}")
        # Log the error but don't raise it - allow the program to continue
        self.page.reload()  # Try refreshing the page
        time.sleep(2)  # Give some time for the page to reload
        logger.info("Page reloaded after timeout")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(3),
        retry=retry_if_exception_type(PlaywrightTimeoutError)
    )
    def handle_station_selection(self):
        """Handle station code selection with retry logic."""
        logger.info(f"Selecting station code: {self.station_code}")
        self.page.wait_for_load_state("networkidle")
        self.page.locator("#vs2__combobox").scroll_into_view_if_needed()
        self.wait_between_inputs()
        self.page.locator("#vs2__combobox").get_by_label("Loading...").click()
        self.wait_between_inputs()
        self.page.get_by_role("option", name=self.station_code).click()
        logger.info("Station code selected successfully")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(3),
        retry=retry_if_exception_type(PlaywrightTimeoutError)
    )
    def handle_observer_selection(self):
        """Handle observer selection with retry logic."""
        logger.info(f"Selecting observer: {self.observer}")
        self.page.wait_for_load_state("networkidle")
        self.wait_between_inputs()
        self.page.get_by_label("Loading...", exact=True).click()
        self.wait_between_inputs()
        self.page.get_by_role("option", name=self.observer).click(timeout=10000)
        logger.info("Observer selected successfully")

    def handle_date_selection(self, day: str):
        """Handle date selection.
        
        Args:
            day: Day of the month
        """
        logger.info("Selecting date...")
        current_day = datetime.now().day
        current_month = datetime.now().month
        current_year = datetime.now().year

        self.wait_between_inputs()
        self.page.locator("#datepicker__value_").click()
        self.wait_between_inputs()
        
        if int(day) == current_day:
            self.page.get_by_label(f"{current_month}/{day}/{current_year} (Today)").click()
        else:
            self.page.get_by_label(f"{current_month}/{day}/{current_year}").click()
        logger.info("Date selected successfully")

    def handle_time_selection(self, hour: str, minute: str):
        """Handle time selection.
        
        Args:
            hour: Hour in 24-hour format
            minute: Minute
        """
        logger.info("Selecting time...")
        self.wait_between_inputs()
        self.page.get_by_label("Jam").select_option(hour)
        self.wait_between_inputs()
        self.page.get_by_label("Menit").select_option(minute)
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(2000)
        logger.info("Time selected successfully")

    def handle_wind_direction(self, direction: str, is_vrb: bool = False):
        """Handle wind direction input.
        
        Args:
            direction: Wind direction in degrees
            is_vrb: Whether the wind is variable
        """
        logger.info("Setting wind direction...")
        self.wait_between_inputs()
        
        # Convert VRB to 000 for the numeric input
        actual_direction = "000" if direction == "VRB" else direction
        
        try:
            time.sleep(1)
            self.page.get_by_label("Arah Angin (derajat)").click()
            self.wait_between_inputs()
            self.page.get_by_label("Arah Angin (derajat)").fill(actual_direction)
            self.wait_between_inputs()
            self.page.get_by_label("Arah Angin (derajat)").press("Tab")
            
            # If it was VRB, check the VRB checkbox
            if is_vrb:
                self.wait_between_inputs()
                self.page.get_by_label("VRB").click()
            logger.info("Wind direction set successfully")
        except PlaywrightTimeoutError as e:
            self.handle_timeout_error(str(e))
            # Try one more time
            self.page.get_by_label("Arah Angin (derajat)").fill(actual_direction)
            if is_vrb:
                self.page.get_by_label("VRB").click()

    def handle_wind_speed(self, speed: str):
        """Handle wind speed input.
        
        Args:
            speed: Wind speed in knots
        """
        logger.info("Setting wind speed...")
        self.wait_between_inputs()
        self.page.get_by_label("Kecepatan Angin (knot)").click()
        self.wait_between_inputs()
        self.page.get_by_label("Kecepatan Angin (knot)").fill(speed)
        logger.info("Wind speed set successfully")

    def handle_wind_variation(self, var_from: str, var_to: str):
        """Handle wind direction variation.
        
        Args:
            var_from: Starting direction of variation
            var_to: Ending direction of variation
        """
        logger.info("Setting wind variation...")
        self.wait_between_inputs()
        self.page.locator("#winds-wd-dn").click()
        self.wait_between_inputs()
        self.page.locator("#winds-wd-dn").fill(var_from)
        self.wait_between_inputs()
        self.page.locator("#winds-wd-dn").press("Tab")
        self.wait_between_inputs()
        self.page.locator("#winds-wd-dx").fill(var_to)
        self.wait_between_inputs()
        self.page.locator("#winds-wd-dx").press("Tab")
        logger.info("Wind variation set successfully")

    def handle_visibility(self, visibility: str, is_cavok: bool = False):
        """Handle visibility input.
        
        Args:
            visibility: Visibility in meters
            is_cavok: Whether CAVOK conditions are present
        """
        logger.info("Setting visibility...")
        if is_cavok:
            self.wait_between_inputs()
            self.page.get_by_label("Kecepatan Angin (knot)").press("Tab")
            self.wait_between_inputs()
            self.page.get_by_label("Gust (Knot)").press("Tab")
            self.wait_between_inputs()
            self.page.locator("#tooltips13").press("Tab")
            self.page.keyboard.press("Space")
            self.page.keyboard.press("Space")
        else:
            self.wait_between_inputs()
            self.page.get_by_role("spinbutton", name="Prevailling (m) Jarak pandang").fill(visibility)
            self.wait_between_inputs()
            self.page.get_by_role("spinbutton", name="Prevailling (m) Jarak pandang").press("Tab")
        logger.info("Visibility set successfully")

    def handle_weather_phenomena(self, phenomena: list):
        """Handle weather phenomena input.
        
        Args:
            phenomena: List of weather phenomena codes
        """
        if not phenomena:
            return

        logger.info("Setting weather phenomena...")
        self.wait_between_inputs()
        self.page.locator(".col-sm-4 > .btn").first.click()
        
        for phenomenon in phenomena:
            self.wait_between_inputs()
            if phenomenon == "TS":
                self.page.get_by_label("Weather", exact=True).get_by_text("TS Thunderstorm").click()
            elif phenomenon == "RA":
                self.page.locator("label").filter(has_text="RA Rain").click()
            elif phenomenon == "-RA":
                self.page.locator("label").filter(has_text="RA Rain").click()
        
        self.wait_between_inputs()
        self.page.get_by_role("button", name="OK").click()
        logger.info("Weather phenomena set successfully")

    def handle_single_cloud_layer(self, cloud_type: str, height: str, subtype: str = None):
        """Handle single cloud layer input.
        
        Args:
            cloud_type: Type of cloud (FEW, SCT, BKN, OVC)
            height: Cloud base height in hundreds of feet (e.g., "020" for 2000 feet)
            subtype: Cloud subtype (CB, TCU) if applicable
        """
        logger.info(f"Setting cloud layer: {cloud_type} {height} {subtype or ''}")
        
        # Convert height from hundreds of feet to actual feet
        # e.g., "020" becomes "2000", "018" becomes "1800"
        actual_height = str(int(height) * 100)
        
        self.wait_between_inputs()
        self.page.get_by_label("General").locator("#clouds-jumlah").select_option(cloud_type)
        self.wait_between_inputs()
        self.page.get_by_label("General").locator("#cloud_height").fill(actual_height)
        
        if subtype in ['CB', 'TCU']:
            self.wait_between_inputs()
            self.page.get_by_label("General").locator("#select-type").select_option(subtype)
        
        self.wait_between_inputs()
        cloud_name = f"{cloud_type} ({self._get_okta_range(cloud_type)}) {subtype or '-'}"
        self.page.get_by_role("row", name=cloud_name).get_by_role("button").click()
        logger.info(f"Cloud layer set successfully with height {actual_height} feet")

    def handle_temperature(self, temperature: str):
        """Handle temperature input.
        
        Args:
            temperature: Temperature in Celsius
        """
        logger.info("Setting temperature...")
        self.wait_between_inputs()
        self.page.locator("#v-air-temp").fill(temperature)
        self.wait_between_inputs()
        self.page.locator("#v-air-temp").press("Tab")
        logger.info("Temperature set successfully")

    def handle_dew_point(self, dew_point: str):
        """Handle dew point input.
        
        Args:
            dew_point: Dew point in Celsius
        """
        logger.info("Setting dew point...")
        self.wait_between_inputs()
        self.page.locator("#v-dew-point").fill(dew_point)
        self.wait_between_inputs()
        self.page.locator("#v-dew-point").press("Tab")
        logger.info("Dew point set successfully")

    def handle_pressure(self, pressure: str):
        """Handle pressure input.
        
        Args:
            pressure: QNH pressure in hPa
        """
        logger.info("Setting pressure...")
        self.wait_between_inputs()
        self.page.get_by_label("TEKANAN UDARA (QNH)").fill(pressure)
        logger.info("Pressure set successfully")

    def handle_trend(self, trend_type: str, trend_details: str = ""):
        """Handle trend information input.
        
        Args:
            trend_type: Type of trend (NOSIG, TEMPO, BECMG)
            trend_details: Additional trend details if applicable
        """
        logger.info("Setting trend information...")
        self.wait_between_inputs()
        self.page.get_by_role("tab", name="Trend").click()
        self.wait_between_inputs()
        self.page.get_by_label("Trend").locator("#input-type").select_option(trend_type)
        
        if trend_details:
            self.wait_between_inputs()
            # Handle trend details if needed
            pass
        logger.info("Trend information set successfully")

    def handle_remarks(self, remarks: str):
        """Handle remarks input.
        
        Args:
            remarks: Remarks text
        """
        if not remarks:
            return
            
        logger.info("Setting remarks...")
        self.wait_between_inputs()
        self.page.get_by_placeholder("Remark").click()
        self.wait_between_inputs()
        self.page.get_by_placeholder("Remark").fill(remarks)
        logger.info("Remarks set successfully")

    def handle_form_submission(self, preview_only: bool = True):
        """Handle form submission.
        
        Args:
            preview_only: Whether to only preview or also submit
        """
        logger.info("Handling form submission...")
        self.wait_between_inputs()
        self.page.get_by_role("button", name="Preview").click()
        
        if not preview_only:
            self.wait_between_inputs()
            self.page.get_by_role("button", name="Submit").click()
        logger.info("Form submission handled successfully")

    @staticmethod
    def _get_okta_range(cloud_type: str) -> str:
        """Get okta range for cloud type.
        
        Args:
            cloud_type: Type of cloud
            
        Returns:
            str: Okta range description
        """
        ranges = {
            "FEW": "1-2 oktas",
            "SCT": "3-4 oktas",
            "BKN": "5-7 oktas",
            "OVC": "8 oktas"
        }
        return ranges.get(cloud_type, "")

    def fill_form(self, metar_data: dict):
        """Fill the METAR form with provided data.
        
        Args:
            metar_data: Dictionary containing METAR data
        """
        try:
            # Ensure we're on the correct page before starting
            self.ensure_page_loaded()

            try:
                # Station and observer
                self.handle_station_selection()
                self.handle_observer_selection()

                # Date and time
                self.handle_date_selection(metar_data['day'])
                self.handle_time_selection(metar_data['hour'], metar_data['minute'])

                # Wind information
                is_vrb = metar_data['wind_direction'] == 'VRB'
                self.handle_wind_direction(metar_data['wind_direction'], is_vrb)
                self.handle_wind_speed(metar_data['wind_speed'])
                
                if metar_data.get('wind_variable_from') and metar_data.get('wind_variable_to'):
                    self.handle_wind_variation(
                        metar_data['wind_variable_from'],
                        metar_data['wind_variable_to']
                    )

                # Visibility
                self.handle_visibility(
                    metar_data['visibility'],
                    metar_data.get('cavok', False)
                )

                # Weather phenomena
                if metar_data.get('weather'):
                    self.handle_weather_phenomena(metar_data['weather'])

                # Clouds
                if metar_data.get('clouds'):
                    for cloud in metar_data['clouds']:
                        self.handle_single_cloud_layer(
                            cloud['cloud_type'],
                            cloud['cloud_height'],
                            cloud.get('cloud_subtype')
                        )

                # Temperature and pressure
                self.handle_temperature(metar_data['temperature'])
                self.handle_dew_point(metar_data['dew_point'])
                self.handle_pressure(metar_data['pressure'])

                # Trend and remarks
                self.handle_trend(
                    metar_data.get('trend_type', 'NOSIG'),
                    metar_data.get('trend_details', '')
                )
                
                if metar_data.get('remarks'):
                    self.handle_remarks(metar_data['remarks'])

                # Submit form
                self.handle_form_submission(preview_only=True)

            except PlaywrightTimeoutError as e:
                # Handle timeout by attempting recovery
                self.handle_timeout_error(str(e))
            except Exception as e:
                logger.error(f"Error filling form: {e}")
                raise

        except Exception as e:
            logger.error(f"Error in form filling process: {e}")
            # Ensure the error is propagated up
            raise 