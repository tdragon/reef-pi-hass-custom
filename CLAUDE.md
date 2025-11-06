# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Reef-Pi, an open-source reef tank controller. The integration communicates with Reef-Pi devices via REST API to monitor sensors and control equipment.

## Development Commands

### Package Management
- Uses uv (fast Python package manager)
- Install dependencies: `uv sync`
- Pre-commit hooks must be installed manually: `uv run pre-commit install`

### Testing
- Run all tests: `uv run pytest`
- Tests use `pytest-homeassistant-custom-component` and `pytest-asyncio`
- Async tests run with `asyncio_mode = auto`

### Linting
- Uses Ruff for linting and formatting
- Pre-commit hook runs: `ruff --fix --exit-non-zero-on-fix --show-fixes`
- Format with: `ruff-format`

### Manual Linting
```bash
uv run ruff check --fix
uv run ruff format
```

## Architecture

### Core Components

**async_api.py** - ReefApi class handles all HTTP communication with Reef-Pi devices
- Uses httpx for async HTTP requests
- Manages authentication via cookies
- Provides methods for all Reef-Pi API endpoints
- Key exceptions: `CannotConnect`, `InvalidAuth`

**__init__.py** - ReefPiDataUpdateCoordinator is the central data coordinator
- Inherits from Home Assistant's DataUpdateCoordinator
- Polls Reef-Pi API at configurable intervals (default: 1 minute)
- Manages device capabilities (temperature, equipment, pH, pumps, ATO, lights, timers, macros, display)
- Updates all sensor data and device states
- Provides control methods for equipment, lights, ATOs, timers, and display

**config_flow.py** - Configuration UI flow
- Validates connection and authentication
- Supports options flow for update interval and pH sensor disable flag
- Uses host as unique_id to prevent duplicate entries

### Platform Files

Each platform file (sensor.py, switch.py, light.py, binary_sensor.py, button.py) creates Home Assistant entities for:
- **sensor**: Temperature sensors, pH probes, pump status, ATO status
- **switch**: Equipment control, timers, ATO enable/disable
- **light**: Light channels with brightness control
- **binary_sensor**: Inlet states
- **button**: Reboot, poweroff, macro execution

### Data Flow

1. Coordinator authenticates with Reef-Pi on first refresh
2. Fetches capabilities to determine available features
3. Polls all enabled subsystems (temperature, equipment, pH, etc.) at update interval
4. Platform entities read data from coordinator.data via their entity IDs
5. Control commands (switch on/off, light brightness) go through coordinator methods which update both API and local state

### Key Patterns

- All entities use coordinator for data updates (no individual polling)
- Entity unique_ids are formatted as `{host}_{subsystem}_{id}`
- Device info centralizes all entities under a single device in Home Assistant
- DateTime parsing uses custom format: `"%b-%d-%H:%M, %Y"`
- pH sensor can be disabled via config options to avoid intermittent reading issues

### MQTT Implementation

**mqtt_handler.py** - Handles MQTT subscriptions and message processing
- ReefPiMQTTHandler class manages all MQTT operations
- Topic parsing: Converts reef-pi MQTT topics to device updates
  - Equipment: `{prefix}/equipment_{name}_state` → state (0.0/1.0)
  - Temperature: `{prefix}/{name}_reading` → temperature value
  - pH: `{prefix}/{name}_reading` → pH value (4 decimal places)
- Name-to-ID correlation: Uses device names from MQTT topics to look up device IDs (case-insensitive)
- Real-time updates: MQTT messages trigger immediate entity state updates via coordinator

**mqtt_tracker.py** - Tracks MQTT updates and optimizes polling
- ReefPiMQTTTracker class manages all tracking data
- Tracks total message count, last update times per device type and device ID
- Records update source ("mqtt" or "polling") for each device
- Provides `should_skip_polling()` method to optimize API calls
- Skip threshold: 2 minutes (devices with recent MQTT updates skip polling)

**Hybrid Approach with Optimization**:
- API polling discovers devices and maintains name-to-ID mappings
- MQTT provides real-time state updates for existing devices
- Coordinator stores both device data (by ID) and name-to-ID mappings
- MQTT messages update coordinator data, which propagates to entities
- **Polling optimization**: Devices with recent MQTT updates (< 2 min) skip API polling
- Diagnostic sensors show MQTT connection status, message counts, and last update times

## Configuration

Integration added via UI (Configuration → Integrations → Add → "reef pi")

Required fields:
- Host (URL of Reef-Pi device)
- Username
- Password
- Verify TLS (default: false)

Optional configuration (via Options):
- Update interval (seconds) - polling interval for API
- Disable pH sensor (workaround for intermittent readings)
- Enable MQTT (appears only if reef-pi has MQTT enabled) - real-time updates

### MQTT Support

The integration automatically discovers MQTT configuration from reef-pi:
- **Initial setup**: Queries `/api/telemetry` during config flow to detect MQTT availability and prefix
- **Auto-refresh**: MQTT config is refreshed every time options dialog is opened
- If reef-pi has MQTT enabled, an option appears in the integration settings
- Users can enable/disable MQTT updates without manual configuration
- MQTT provides real-time state updates (temperature, equipment, pH)
- API polling continues as fallback and for device discovery

**Upgrade note**: If you had the integration installed before MQTT support was added, simply open the integration options once to auto-discover MQTT settings.

If you change MQTT settings in reef-pi (e.g., change prefix or enable/disable):
1. Open the integration options in Home Assistant
2. MQTT config will automatically refresh and show updated settings
3. Reload the integration if you changed the prefix

### MQTT Diagnostic Sensors

When MQTT is enabled, the integration creates diagnostic sensors (visible in device diagnostics page):
- **MQTT Status** - Shows "connected", "disabled", or "no_messages"
- **MQTT Messages Received** - Total count of MQTT messages (counter)
- **MQTT Last Temperature Update** - Timestamp of last temperature MQTT message
- **MQTT Last Equipment Update** - Timestamp of last equipment MQTT message
- **MQTT Last pH Update** - Timestamp of last pH MQTT message

These sensors help monitor MQTT connectivity and troubleshoot issues.

## Version Management

Current version: 0.3.17 (maintained in both pyproject.toml and manifest.json)

## Known Issues

pH sensors may cause intermittent reading drops. Solution: Disable pH sensor in integration config and use Reef-Pi's MQTT functionality instead.
