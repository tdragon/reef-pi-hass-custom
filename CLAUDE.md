# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Reef-Pi, an open-source reef tank controller. The integration communicates with Reef-Pi devices via REST API to monitor sensors and control equipment.

## Development Commands

### Package Management
- Uses PDM (Python Dependency Manager)
- Install dependencies: `pdm install`
- Pre-commit hooks are automatically installed via `post_install` script

### Testing
- Run all tests: `pdm run pytest`
- Tests use `pytest-homeassistant-custom-component` and `pytest-asyncio`
- Async tests run with `asyncio_mode = auto`

### Linting
- Uses Ruff for linting and formatting
- Pre-commit hook runs: `ruff --fix --exit-non-zero-on-fix --show-fixes`
- Format with: `ruff-format`

### Manual Linting
```bash
pdm run ruff check --fix
pdm run ruff format
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
  - Equipment: `{prefix}/equipment_{name}-state` → state (0.0/1.0)
  - Temperature: `{prefix}/{name}_reading` → temperature value
  - pH: `{prefix}/{name}_reading` → pH value (4 decimal places)
- Name-to-ID correlation: Uses device names from MQTT topics to look up device IDs
- Real-time updates: MQTT messages trigger immediate entity state updates via coordinator

**Hybrid Approach**:
- API polling discovers devices and maintains name-to-ID mappings
- MQTT provides real-time state updates for existing devices
- Coordinator stores both device data (by ID) and name-to-ID mappings
- MQTT messages update coordinator data, which propagates to entities

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
- Queries `/api/telemetry` during setup to detect MQTT availability and prefix
- If reef-pi has MQTT enabled, an option appears in the integration settings
- Users can enable/disable MQTT updates without manual configuration
- MQTT provides real-time state updates (temperature, equipment, pH)
- API polling continues as fallback and for device discovery

## Version Management

Current version: 0.3.17 (maintained in both pyproject.toml and manifest.json)

## Known Issues

pH sensors may cause intermittent reading drops. Solution: Disable pH sensor in integration config and use Reef-Pi's MQTT functionality instead.
