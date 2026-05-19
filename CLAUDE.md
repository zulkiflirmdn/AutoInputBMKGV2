# AutoInput-BMKGsoftV2

## Overview

`AutoInput-BMKGsoftV2` is a modern automated data input application built for the BMKG Satu meteorological platform. It is designed to help meteorological observers and automation operators submit observational data quickly, reliably, and in a repeatable way.

The project combines a graphical user interface with browser automation and weather data parsing:

- A PyQt6-based desktop UI for user interaction, file selection, and execution control.
- Playwright browser automation to operate the BMKG Satu website and fill submission forms automatically.
- METAR processing utilities for parsing METAR weather reports and converting them into structured values.
- Auto-send scheduling that can submit data automatically on hourly cycles.
- A configurable logging and configuration system for easier maintenance.

## What the project does

The core purpose of the project is to automate the process of entering meteorological observation data into the BMKG Satu submission portal. The main tasks it performs are:

1. Load observation input data from structured sources such as Excel or CSV.
2. Open or control a browser session using Playwright.
3. Navigate to the appropriate BMKG Satu form page.
4. Fill observation fields with weather data, cloud observations, wind, pressure, and other required values.
5. Preview the filled form and optionally submit data.
6. Support auto-send workflows for periodic hourly data submission.

## Key components

### `src/ui/modern_app.py`

This file contains the main GUI implementation using PyQt6. It provides:

- File selection controls.
- Browser opening and reload buttons.
- Progress and status updates.
- Buttons for running the automation.
- Worker thread integration for non-blocking browser operations.

### `src/core/autoinput.py`

This class encapsulates the browser form-filling logic. It maps user input values to web form controls and performs the complete automated fill sequence for the BMKG Satu form.

It handles:

- Station and observer selection.
- Observation date and time.
- Wind, visibility, weather, and pressure fields.
- Cloud layer details, including low/medium/high cloud observations.
- Special handling for important observation hours like 00 and 12.

### `src/core/metar_reader.py`

A dedicated parser for METAR weather report strings. It extracts structured data such as:

- Station identifier
- Observation timestamp
- Wind direction and speed
- Visibility and weather phenomena
- Cloud layers
- Temperature, dew point, and pressure
- Trend and remarks

### `src/auto_sender.py`

This module provides an automated submission scheduler. It can:

- Wait until the next full hour.
- Reload the page.
- Fill the form and submit automatically.
- Retry and recover from failures.

### `src/utils/logger.py`

A logging helper used by the application. It configures rotating log files and ensures logging is available for app, browser, and error messages.

### `src/config.py`

Defines configuration data classes and a small loader for external settings. The project also maintains a YAML configuration file in `config/config.yaml`.

## Project structure

```
AutoInput-BMKGsoftV2/
├── config/              # YAML configuration definitions
├── logs/                # Generated runtime log files
├── src/                 # Main application source code
│   ├── core/            # Browser automation and processing logic
│   ├── data/            # Data mapping and default values
│   ├── ui/              # User interface components
│   └── utils/           # Helpers such as logging and retry utilities
├── tests/               # Automated tests
├── requirements.txt     # Runtime dependencies
├── requirements-dev.txt # Development dependencies
├── run.py               # Application entrypoint
├── setup.py             # Packaging definition
└── README.md            # Project summary and usage
```

## How to run

1. Create a Python virtual environment and activate it.
2. Install dependencies with `pip install -r requirements.txt`.
3. Install Playwright browsers with `playwright install`.
4. Run the app using:

```bash
python run.py
```

## Why this project exists

The BMKG Satu platform requires consistent and accurate meteorological data entry. Manual entry is slow, error-prone, and difficult to scale. This project automates that workflow so that observers can focus on data quality rather than repetitive form submission.

## Notes for contributors

- The browser automation layer is tightly coupled to the specific web form structure, so any form redesign will require updating selectors.
- The current architecture separates UI, automation, and data processing, but there is room to improve configuration centralization and error handling.
- Tests should continue expanding around `AutoInput`, `MetarReader`, and configuration flows.

## Summary

`AutoInput-BMKGsoftV2` is a desktop automation tool for BMKG meteorological data submission. It combines a polished UI, browser automation, and weather parsing to streamline the BMKG Satu input workflow.
