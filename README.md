# AutoInput-BMKGsoftV2

AutoInput-BMKGsoftV2 automates meteorological data entry for the BMKG Satu portal.
It uses a desktop UI and browser automation to fill the submission form with observation values.

## What it does

- Opens the BMKG Satu input page and controls the browser automatically.
- Fills observational fields such as wind, temperature, pressure, visibility, and clouds.
- Supports METAR parsing to convert weather reports into form-ready values.
- Provides an optional hourly auto-send workflow for repeated submissions.

## Why it exists

Manual BMKG data entry is repetitive and prone to mistakes.
This project reduces manual effort by automating form completion while preserving user control.

## Quick start

1. Create and activate a Python virtual environment.
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Install Playwright browsers:
```bash
playwright install
```
4. Run the app:
```bash
python run.py
```

## Main components

- `src/ui/modern_app.py` - PyQt6 GUI and workflow controls.
- `src/core/autoinput.py` - Browser automation logic for form filling.
- `src/core/metar_reader.py` - METAR parser for structured weather data.
- `src/auto_sender.py` - Auto-send scheduler for hourly submissions.
- `src/utils/logger.py` - Logging and diagnostics.

## Configuration

Configure browser, automation, and logging settings in `config/config.yaml`.

## License

MIT License.