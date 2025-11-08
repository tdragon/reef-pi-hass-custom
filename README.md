[![Community Forum](https://img.shields.io/badge/Community-Forum-41BDF5.svg?style=popout)](https://community.home-assistant.io/t/reef-pi-home-assistant-integration/312945)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

[![GitHub release](https://img.shields.io/github/release/tdragon/reef-pi-hass-custom.svg)](https://github.com/tdragon/reef-pi-hass-custom/releases)
[![pytest](https://github.com/tdragon/reef-pi-hass-custom/actions/workflows/pytest.yaml/badge.svg)](https://github.com/tdragon/reef-pi-hass-custom/actions/workflows/pytest.yaml)
[![hassfest](https://github.com/tdragon/reef-pi-hass-custom/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/tdragon/reef-pi-hass-custom/actions/workflows/hassfest.yaml)
![GitHub All Releases](https://img.shields.io/github/downloads/tdragon/reef-pi-hass-custom/total)
![GitHub Latest Release](https://img.shields.io/github/downloads/tdragon/reef-pi-hass-custom/latest/total)

<p align="center">
  <img src="assets/icon.png" alt="Reef-Pi Integration Icon" width="256"/>
</p>

# Home Assistant Reef Pi Integration

This custom integration provides a way to monitor sensors data and control equipment connected to [Reef-Pi (An open source reef tank controller based on Raspberry Pi)](http://reef-pi.github.io/) ([GIT repository](https://github.com/reef-pi/reef-pi/releases)).

## Installation

### Using [HACS](https://hacs.xyz/) (recommended)

This integration can be installed using HACS.
To do it add custom *integration* repository using url: `https://github.com/tdragon/reef-pi-hass-custom/`.
Then search for Reef Pi in the *Integrations* section.
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tdragon&repository=reef-pi-hass-custom&category=Integration)

### Manual
To install this integration manually you have to download the content of this repository to `config/custom_components/reef-pi-hass-custom` directory:
```bash
mkdir -p custom_components/reef_pi
cd custom_components/reef_pi
curl -s https://api.github.com/repos/tdragon/reef-pi-hass-custom/releases/latest | grep "/reef_pi.zip"|cut -d : -f 2,3|tr -d \"| wget -i -
unzip reef_pi.zip
rm reef_pi.zip
```
After that restart Home Assistant.

## Configuration
Install integration from UI (Configuration --> Integrations --> + --> Search for `reef pi`)
Configuration options:
- Host (http://ip.address or https://ip.address)
- user name
- password
  
## Usage
Integration creates temperature sensor for each sensor connected to Reef PI: `sensor.{reef-pi name}_{temperature_sensor_name}`
Additionally, it creates one sensor for CPU temperature: `sensor.{reef_pi_name}`

For each equipment configured in Reef Pi an outlet entity is created: `switch.{reef_pi name}_{equipment_name}`

Additional entities include:
- `switch.{reef_pi name}_display` to toggle the reef-pi display on or off.
- `button.{reef_pi name}_reboot` and `button.{reef_pi name}_poweroff` for rebooting or shutting down the controller.

## MQTT Support

The integration supports **optional MQTT** for real-time updates, significantly reducing API polling and providing instant state changes.

### Features
- **Real-time updates** for temperature, pH, and equipment state changes
- **Intelligent polling optimization** - skips API calls for devices with recent MQTT updates
- **Automatic discovery** - MQTT configuration detected from reef-pi automatically
- **Diagnostic sensors** - monitor MQTT connection status, message counts, and last update times

### How to Enable

**Prerequisites:**
- reef-pi must have MQTT enabled (Settings → Telemetry → MQTT)
- Home Assistant must have MQTT integration configured and connected to the same broker

**Steps:**
1. Open your reef-pi integration in Home Assistant (Settings → Devices & Services → reef-pi → Configure)
2. If reef-pi has MQTT enabled, you'll see an "Enable MQTT" checkbox
3. Check the box and click "Submit"
4. Verify MQTT is working by checking the diagnostic sensors (MQTT Status, MQTT Messages Received)

### Multiple reef-pi Instances

⚠️ **Important:** If you run multiple reef-pi controllers, each instance **must** have a unique MQTT prefix to avoid device collisions!

Configure unique prefixes in each reef-pi instance (Settings → Telemetry → MQTT → Prefix):
- reef-pi #1: `reef-pi/main-tank`
- reef-pi #2: `reef-pi/frag-tank`
- reef-pi #3: `reef-pi/sump`

Without unique prefixes, MQTT messages from different controllers will interfere with each other.

### Diagnostic Sensors

When MQTT is enabled, the following diagnostic sensors are created:
- **MQTT Status** - Connection status ("connected", "disabled", "no_messages")
- **MQTT Messages Received** - Total message count
- **MQTT Last Temperature Update** - Timestamp of last temperature MQTT message
- **MQTT Last Equipment Update** - Timestamp of last equipment MQTT message
- **MQTT Last pH Update** - Timestamp of last pH MQTT message

These sensors are visible in the device diagnostics view.

## NOTE: How to "fix" intermittent pH readings
On some installations of this addon, it can cause Reef Pi to intermittently drop the reading from both the Reef Pi graph/database and in Home Assistant.

To fix this:
1. In Home Assistant go to Settings → Integrations → Reef-Pi integration
2. Under "Integration entries" click on "Configure"
3. Select "Disable pH sensor" and click "Submit"
4. Click the 3 vertical dots and select "Reload"

To continue monitoring pH in Home Assistant, enable MQTT support (see "MQTT Support" section above) which provides real-time pH readings without the intermittent drop issues.
