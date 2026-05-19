# AutoInput-BMKGsoftV2

## Overview

`AutoInput-BMKGsoftV2` is a modern automated data input application built for the BMKG Satu meteorological platform. It automates synoptic observation data entry for meteorological observers and station operators.

The project combines:

- A PyQt6-based desktop UI with tabbed interface for form filling, METAR processing, and auto-send control.
- Playwright browser automation that controls a persistent Chromium session to fill BMKG Satu submission forms.
- METAR parsing that converts aviation weather codes into structured observational values.
- Hourly auto-send scheduling with retry logic and error recovery.
- YAML-based configuration and rotating log file management.

## What the project does

1. Load observation data from Excel or CSV files, keyed by observation hour.
2. Launch or reuse a persistent Chromium browser session via Playwright.
3. Navigate to the BMKG Satu synoptic input form.
4. Fill all fields: station, observer, date/time, wind, visibility, weather, pressure, temperature, and cloud layers.
5. Preview and optionally submit the completed form.
6. Run hourly auto-send cycles with exponential backoff retry and error tracking.

## Project structure

```
AutoInput-BMKGsoftV2/
├── .github/workflows/ci.yml     # CI/CD pipeline
├── config/
│   └── config.yaml              # Main YAML configuration
├── legacy/                      # Deprecated code (not in active use)
│   ├── autosend_synop.py
│   ├── browsermanager.py
│   └── metar.py
├── logs/                        # Runtime rotating log files
├── src/
│   ├── config.py                # Configuration dataclasses (RetryConfig, NetworkConfig, AutoSenderConfig)
│   ├── exceptions.py            # Custom exceptions (PageLoadError, FormFillError, etc.)
│   ├── auto_sender.py           # Hourly auto-send scheduler
│   ├── core/
│   │   ├── autoinput.py         # Main form-filling automation (AutoInput class)
│   │   ├── browsermanager.py    # Browser lifecycle management (BrowserManager)
│   │   ├── browserloader.py     # Playwright browser initialization (BrowserLoader)
│   │   ├── formfiller.py        # Async form filler (FormFiller, less active)
│   │   ├── metar_processor.py   # High-level METAR page interaction (MetarProcessor)
│   │   └── metar_reader.py      # METAR string parser (MetarReader)
│   ├── data/
│   │   ├── sandi.py             # BMKG code mappings, observer list, default input template
│   │   ├── user_input.py        # Excel/CSV data loader (UserInputUpdater)
│   │   └── input.py             # Legacy/placeholder (InputProcessor)
│   ├── ui/
│   │   ├── modern_app.py        # Main PyQt6 window, tabs, PersistentWorkerThread
│   │   ├── metar_tab.py         # METAR input tab widget (MetarTab)
│   │   ├── auto_send_control.py # Auto-send UI control (AutoSendControl, tkinter-based)
│   │   ├── app.py               # Legacy UI (not actively used)
│   │   └── assets/bmkg.ico      # Application icon
│   └── utils/
│       ├── logger.py            # Logging setup with rotating handlers (app, browser, error logs)
│       ├── config.py            # YAML + .env config loader with dot-notation access
│       └── retry.py             # Retry decorator (with_retry) and ErrorTracker class
├── tests/
│   ├── test_autoinput.py        # AutoInput unit tests with mock page fixtures
│   └── test_metar_reader.py     # MetarReader tests (13 cases: CAVOK, CB, VRB wind, etc.)
├── requirements.txt
├── requirements-dev.txt
├── run.py                       # Entry point → src.ui.modern_app:main
└── setup.py                     # Package: autoinput-bmkgsoftv2 v0.2.0
```

## Key components

### `src/core/autoinput.py` — AutoInput

The central class that drives form filling. It receives a `user_input` dict and a Playwright `page`, then fills every field of the BMKG Satu synoptic form in sequence:

- Station and observer selection
- Observation date and time
- Wind, visibility, present/past weather
- Temperature, dew point, pressure
- Low/medium/high cloud layers with type codes
- Special handling for 00Z and 12Z observation hours

### `src/core/metar_reader.py` — MetarReader

Parses a raw METAR string into a structured dict. Handles:

- Variable and calm wind (`VRB`, `00000KT`)
- CAVOK
- Multiple weather phenomena
- Cloud layers with subtypes (`CB`, `TCU`)
- Negative temperatures
- Trend and remarks sections

### `src/core/browsermanager.py` — BrowserManager

Manages the Playwright browser lifecycle. Launches a persistent Chromium context saved to a user data directory (for session persistence), navigates between the auto-input page and METAR page, and runs at 1920×1080 full-screen.

### `src/auto_sender.py` — AutoSender

Hourly scheduler that:

1. Calculates time to the next full hour and sleeps.
2. Reloads the page and fills the form for that hour.
3. Executes the View → Preview → OK → Send chain.
4. Recovers from page errors with reload + navigation fallback.
5. Tracks cumulative errors via `ErrorTracker` and reports stats on stop.

Uses `AutoSenderState` dataclass for mutable running state and calls progress callbacks for real-time UI updates.

### `src/data/sandi.py` — Code Mappings

Contains all BMKG-specific lookup tables used during form filling:

- `STATION_CODE`, `DEFAULT_OBSERVER`
- `obs`: observer name → display name
- `ww`, `w1w2`: present and past weather code maps
- `awan_lapisan`: cloud layer type codes
- `arah_angin`: wind direction strings
- `ci`, `cm`, `ch`: cloud type codes per level
- `default_user_input`: default observation data template

### `src/ui/modern_app.py` — Main UI

PyQt6 application window with three tabs:

- **Auto Input**: file selection, run/preview buttons, progress log
- **METAR**: paste METAR string, process, view structured output
- **Auto-Send**: start/stop scheduler, headless toggle

Uses `PersistentWorkerThread` (QThread with a command queue) to keep browser operations off the main thread.

### `src/utils/retry.py` — Retry & Error Tracking

- `with_retry(max_retries, initial_delay, max_delay, backoff_factor, exceptions)`: decorator with exponential backoff
- `ErrorTracker`: aggregates error counts by type for summary reporting

### `src/utils/logger.py` — Logging

Configures three rotating file handlers (10 MB, 5 backups):

- `logs/app.log` — general application events
- `logs/browser.log` — Playwright automation events
- `logs/error.log` — errors with full tracebacks

## Configuration

`config/config.yaml` defines:

| Section | Key settings |
|---|---|
| `paths` | `user_data_dir`, `log_dir`, `temp_dir` |
| `logging` | `level`, `max_size` (10 MB), `backup_count` |
| `browser` | `type: chromium`, `headless: false`, `timeout: 30000ms`, viewport |
| `ui` | `window_size`, `theme`, colors |
| `automation` | `retry_count: 3`, `retry_delay`, `wait_timeout`, field validation ranges |

`src/utils/config.py` (`Config` class) loads this file and supports `.env` overrides, dot-notation `get(key, default)`, and `save()`.

## Dependencies

**Runtime** (`requirements.txt`):
- `playwright>=1.40.0` — browser automation
- `PyQt6>=6.4.0` — desktop UI
- `pandas>=2.0.0`, `openpyxl>=3.1.0` — Excel/CSV data loading
- `tenacity>=9.1.2` — retry logic
- `PyYAML>=6.0.1`, `python-dotenv>=1.0.0` — configuration

**Dev** (`requirements-dev.txt`):
- `pytest`, `pytest-playwright`, `pytest-mock`, `pytest-cov`
- `black`, `flake8`, `mypy`, `isort`, `pre-commit`
- `Sphinx` — documentation

## How to run

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
playwright install
python run.py
```

Entry point: `run.py` → `src.ui.modern_app:main`

The installed CLI command is `bmkg-autoinput`.

## Testing

```bash
pytest tests/
pytest tests/test_metar_reader.py -v   # 13 METAR test cases
pytest tests/test_autoinput.py -v      # AutoInput with mock page
```

## Notes for contributors

- Browser selectors in `autoinput.py` are tightly coupled to the BMKG Satu form structure; any site update requires selector updates.
- `legacy/` contains deprecated code and should not be imported.
- `src/data/input.py` and `src/ui/app.py` are largely unused — prefer `autoinput.py` and `modern_app.py`.
- `src/ui/auto_send_control.py` uses tkinter/ttk while the rest of the UI uses PyQt6 — this is a known inconsistency.
- The `formfiller.py` async path is less tested; the primary filling path is the synchronous `AutoInput` class.
- Expand tests around `AutoSender`, `BrowserManager`, and configuration loading.
- Station code and default observer are hardcoded in `src/data/sandi.py` — move to config if multi-station support is needed.

## Summary

`AutoInput-BMKGsoftV2` is a desktop automation tool for BMKG Satu meteorological data submission. It combines a tabbed PyQt6 interface, persistent Playwright browser control, METAR parsing, hourly auto-send scheduling, and robust retry/logging infrastructure to streamline the BMKG Satu synoptic input workflow.
