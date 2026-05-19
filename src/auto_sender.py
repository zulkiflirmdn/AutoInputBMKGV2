import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable, Any, Dict
from playwright.sync_api import Playwright, sync_playwright, Page
import re
import logging
from dataclasses import dataclass

from .data.sandi import obs, ww, w1w2, awan_lapisan, arah_angin, ci, cm, ch
from .data import default_user_input, UserInputUpdater
from .utils import get_logger
from .exceptions import (
    AutoSenderError, PageLoadError, FormFillError,
    FormSubmitError, NetworkError, ConfigurationError
)
from .utils.retry import with_retry, ErrorTracker
from .config import AutoSenderConfig, RetryConfig, NetworkConfig

logger = get_logger(__name__)

@dataclass
class AutoSenderState:
    """Class to track AutoSender state."""
    is_running: bool = False
    first_run: bool = True
    last_run_hour: Optional[int] = None
    error_tracker: ErrorTracker = ErrorTracker()

class AutoSender:
    def __init__(
        self,
        page: Optional[Page] = None,
        config: Optional[AutoSenderConfig] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
        file_path: Optional[str] = None,
    ):
        """
        Initialize AutoSender with configuration and optional page.

        Args:
            page: Optional Playwright page instance
            config: Optional configuration object
            progress_callback: Optional callback for progress updates
            file_path: Path to Excel/CSV file with hourly observation data
        """
        self.config = config or AutoSenderConfig()
        self.page = page
        self.state = AutoSenderState()
        self.progress_callback = progress_callback
        self.file_path = file_path
        self.user_input = default_user_input.copy()
        logger.info("AutoSender initialized with configuration")

    def get_next_full_hour(self) -> datetime:
        """Calculate the next full hour from current time."""
        now = datetime.now()
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return next_hour

    def wait_until_next_hour(self) -> None:
        """Wait until the next full hour with progress updates."""
        next_hour = self.get_next_full_hour()
        wait_seconds = (next_hour - datetime.now()).total_seconds()
        
        if wait_seconds > 0:
            message = f"Waiting {wait_seconds:.0f} seconds until {next_hour.strftime('%H:%M')}"
            logger.info(message)
            if self.progress_callback:
                self.progress_callback(message)
            time.sleep(wait_seconds)

    @with_retry(
        max_retries=5,
        initial_delay=1.0,
        max_delay=30.0,
        backoff_factor=2.0,
        exceptions=(PageLoadError, NetworkError)
    )
    def wait_for_element(self, selector: str, timeout: int = 10000) -> bool:
        """Wait for element with improved retry mechanism."""
        try:
            self.page.wait_for_selector(selector, timeout=timeout, state="visible")
            logger.debug(f"Element '{selector}' found and visible")
            return True
        except Exception as e:
            raise PageLoadError(f"Failed to find element '{selector}'", e)

    @with_retry(
        max_retries=3,
        initial_delay=2.0,
        max_delay=20.0,
        backoff_factor=2.0,
        exceptions=(FormFillError, NetworkError)
    )
    def fill_form(self, current_hour: int) -> bool:
        """Fill the complete form using AutoInput with data for the current hour."""
        from .core.autoinput import AutoInput

        try:
            # Reload page before filling
            self.page.reload()
            self.page.wait_for_load_state("networkidle")

            # Start with defaults then override with file data for this hour
            user_input = self.user_input.copy()
            user_input['jam_pengamatan'] = str(current_hour)

            if self.file_path:
                try:
                    updater = UserInputUpdater(user_input)
                    user_input = updater.update_from_file(
                        self.file_path, current_hour, "input_data"
                    )
                    logger.info(f"Loaded observation data from file for hour {current_hour:02d}:00")
                except Exception as e:
                    logger.warning(f"Could not load from file ({e}), using default values")

            auto_input = AutoInput(
                self.page, user_input,
                obs, ww, w1w2, awan_lapisan, arah_angin, ci, cm, ch
            )
            # preview=False: AutoInput fills the form but does not click Preview.
            # submit_form() handles the full View → Preview → OK → Send chain.
            auto_input.fill_form(preview=False)
            logger.info(f"Form filled for hour {current_hour:02d}:00")
            return True

        except Exception as e:
            self.state.error_tracker.log_error("form_fill", e)
            raise FormFillError(f"Error filling form: {str(e)}", e)

    @with_retry(
        max_retries=3,
        initial_delay=2.0,
        max_delay=20.0,
        backoff_factor=2.0,
        exceptions=(FormSubmitError, NetworkError)
    )
    def submit_form(self) -> bool:
        """Submit the form and send data.

        Handles both modes:
          - New observation  → 'Preview & Generate Sandi' → 'Send'
          - Edit existing    → 'Preview & Generate Sandi' → 'Send & Update'
        """
        try:
            logger.info("Starting data submission process...")

            # Generate the SYNOP code / preview
            preview_btn = self.page.get_by_role("button", name="Preview & Generate Sandi")
            preview_btn.wait_for(state="visible", timeout=10000)
            preview_btn.click()
            time.sleep(2)

            # Dismiss any SweetAlert2 or confirmation modal
            swal = self.page.locator(".swal2-popup")
            if swal.count() > 0 and swal.first.is_visible():
                confirm = self.page.locator(".swal2-confirm")
                if confirm.count() > 0:
                    confirm.first.click()
                    time.sleep(0.5)

            # Detect mode: prefer "Send & Update" (edit), fall back to "Send" (new)
            send_update = self.page.get_by_role("button", name="Send & Update")
            send_only   = self.page.get_by_role("button", name="Send")

            if send_update.count() > 0 and send_update.first.is_visible():
                logger.info("Edit mode detected — clicking 'Send & Update'")
                send_update.first.click()
            elif send_only.count() > 0 and send_only.first.is_visible():
                logger.info("New mode detected — clicking 'Send'")
                send_only.first.click()
            else:
                raise FormSubmitError("Neither 'Send' nor 'Send & Update' button found after preview.")

            time.sleep(1)

            # Dismiss post-send confirmation if it appears
            swal2 = self.page.locator(".swal2-popup")
            if swal2.count() > 0 and swal2.first.is_visible():
                confirm2 = self.page.locator(".swal2-confirm")
                if confirm2.count() > 0:
                    confirm2.first.click()
                    time.sleep(0.5)

            logger.info("Data submitted successfully!")
            return True
        except Exception as e:
            self.state.error_tracker.log_error("form_submit", e)
            raise FormSubmitError(f"Error submitting form: {str(e)}", e)

    @with_retry(
        max_retries=3,
        initial_delay=2.0,
        max_delay=20.0,
        backoff_factor=2.0,
        exceptions=(NetworkError, PageLoadError)
    )
    def handle_page_error(self) -> bool:
        """Handle page errors and attempt recovery."""
        try:
            logger.debug("Attempting to reload page...")
            self.page.reload()
            self.page.wait_for_load_state("networkidle")
            return True
        except Exception as e:
            self.state.error_tracker.log_error("page_reload", e)
            try:
                logger.debug("Attempting to access page again...")
                self.page.goto(self.config.base_url)
                self.page.wait_for_load_state("networkidle")
                return True
            except Exception as goto_error:
                self.state.error_tracker.log_error("page_access", goto_error)
                raise NetworkError(f"Failed to recover page: {str(goto_error)}", goto_error)

    def start(self) -> None:
        """Start the auto-send process with enhanced error handling and logging."""
        if not self.page:
            raise ConfigurationError("No browser page provided")

        # Reset state before starting
        self.state = AutoSenderState()
        self.state.is_running = True
        logger.info("Auto-send process started")
        
        if self.progress_callback:
            self.progress_callback("Auto-send process started")
        
        try:
            while self.state.is_running:
                try:
                    # Wait until next full hour first
                    if self.progress_callback:
                        next_hour = self.get_next_full_hour()
                        self.progress_callback(f"Waiting until next hour ({next_hour.strftime('%H:%M')})")
                    
                    self.wait_until_next_hour()
                    
                    if not self.state.is_running:
                        logger.info("Auto-send process stopped during wait")
                        if self.progress_callback:
                            self.progress_callback("Auto-send process stopped during wait")
                        break

                    # Get the current hour AFTER waiting for the next full hour
                    current_time = datetime.now()
                    current_hour = current_time.hour
                    
                    if self.progress_callback:
                        self.progress_callback(f"Processing data for hour {current_hour}:00")
                    
                    # If this is the first run, reload the page before starting
                    if self.state.first_run:
                        logger.info("First run detected - reloading page to ensure fresh start")
                        if self.progress_callback:
                            self.progress_callback("First run - reloading page")
                        self.page.reload()
                        self.page.wait_for_load_state("networkidle")
                        self.state.first_run = False
                    
                    logger.info(f"Starting data submission for hour {current_hour}:00")
                    
                    # Fill and submit form
                    if self.fill_form(current_hour) and self.submit_form():
                        self.state.last_run_hour = current_hour
                        success_msg = f"Data submitted successfully for {current_hour}:00"
                        logger.info(success_msg)
                        if self.progress_callback:
                            self.progress_callback(success_msg)
                        
                        # Wait 2 minutes before reloading
                        if self.progress_callback:
                            self.progress_callback("Waiting 2 minutes before reload...")
                        time.sleep(2 * 60)
                        
                        # Always reload the page after 2 minutes
                        if self.progress_callback:
                            self.progress_callback("Reloading page...")
                        try:
                            self.page.reload()
                            self.page.wait_for_load_state("networkidle")
                            if self.progress_callback:
                                self.progress_callback("Page reloaded successfully")
                        except Exception as e:
                            self.state.error_tracker.log_error("page_reload", e)
                            if self.progress_callback:
                                self.progress_callback(f"Error reloading page: {str(e)}")
                            self.handle_page_error()
                    else:
                        error_msg = "Form submission failed"
                        logger.error(error_msg)
                        if self.progress_callback:
                            self.progress_callback(error_msg)
                        time.sleep(60)

                except Exception as e:
                    self.state.error_tracker.log_error("main_loop", e)
                    error_msg = f"Error in auto-send: {str(e)}"
                    if self.progress_callback:
                        self.progress_callback(error_msg)
                    if self.state.is_running:
                        retry_msg = "Retrying in 1 minute..."
                        logger.warning(retry_msg)
                        if self.progress_callback:
                            self.progress_callback(retry_msg)
                        time.sleep(60)
                        try:
                            self.page.reload()
                            self.page.wait_for_load_state("networkidle")
                        except Exception as reload_error:
                            self.state.error_tracker.log_error("page_reload", reload_error)
                            if self.progress_callback:
                                self.progress_callback(f"Error reloading page: {str(reload_error)}")
                            time.sleep(300)

        except Exception as e:
            self.state.error_tracker.log_error("fatal_error", e)
            fatal_error_msg = f"Fatal error in auto-send process: {str(e)}"
            logger.error(fatal_error_msg)
            if self.progress_callback:
                self.progress_callback(fatal_error_msg)
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the auto-send process and log final statistics."""
        if self.state.is_running:
            logger.info("Stopping auto-send process...")
            self.state.is_running = False
            
            # Log final error statistics
            error_summary = self.state.error_tracker.get_error_summary()
            logger.info(f"Final error statistics: {error_summary}")
            
            # Reset state but keep page reference
            self.state = AutoSenderState()
            
            if self.progress_callback:
                self.progress_callback("Auto-send process stopped")
            
            logger.info("Auto-send process stopped")
