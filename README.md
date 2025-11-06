[![Community Forum](https://img.shields.io/badge/Community-Forum-41BDF5.svg?style=popout)](https://community.home-assistant.io/t/reef-pi-home-assistant-integration/312945)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

[![GitHub release](https://img.shields.io/github/release/tdragon/reef-pi-hass-custom.svg)](https://github.com/tdragon/reef-pi-hass-custom/releases)
[![pytest](https://github.com/tdragon/reef-pi-hass-custom/actions/workflows/pytest.yaml/badge.svg)](https://github.com/tdragon/reef-pi-hass-custom/actions/workflows/pytest.yaml)
[![hassfest](https://github.com/tdragon/reef-pi-hass-custom/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/tdragon/reef-pi-hass-custom/actions/workflows/hassfest.yaml)
![GitHub All Releases](https://img.shields.io/github/downloads/tdragon/reef-pi-hass-custom/total)
![GitHub Latest Release](https://img.shields.io/github/downloads/tdragon/reef-pi-hass-custom/latest/total)


# Home Assistant Reef Pi Integration

This custom integration provides a way to monitor sensors data and control equipment connected to [Reef-Pi (An open source reef tank controller based on Raspberry Pi)](http://reef-pi.github.io/) ([GIT repository](https://github.com/reef-pi/reef-pi/releases)).

## Installation

### Using [HACS](https://hacs.xyz/) (recommended)

This integration can be installed using HACS.
To do it add custom *integration* repository using url: `https://github.com/tdragon/reef-pi-hass-custom/`.
Then search for Reef Pi in the *Integrations* section.

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

## pH Probe Calibration

The integration provides services to calibrate pH probes directly from Home Assistant. Both saltwater and freshwater systems use two-point calibration with **midpoint** and **highpoint** services, but with different pH buffer values.

### Services Available

1. **`reef_pi.calibrate_ph_midpoint`** - First calibration point
   - Target: pH sensor entity
   - Parameters:
     - `expected`: The expected pH value (7.0 for saltwater, 4.0 for freshwater)

2. **`reef_pi.calibrate_ph_highpoint`** - Second calibration point
   - Target: pH sensor entity
   - Parameters:
     - `expected`: The expected pH value (10.0 for saltwater, 7.0 for freshwater)

3. **`reef_pi.set_ph_probe_enabled`** - Enable or disable a pH probe
   - Target: pH sensor entity
   - Parameters:
     - `enabled`: `true` to enable, `false` to disable

### Calibration Workflows

#### Monitoring pH Readings During Calibration

To see if readings have stabilized:

1. **View your pH sensor** in Home Assistant (e.g., `sensor.reef_pi_ph`)
   - Go to **Developer Tools → States** and find your pH sensor
   - Or add the pH sensor to a dashboard for easier monitoring
   - Or use the **History** view to see the reading trend

2. **Watch for stabilization** - The reading should:
   - Stop changing for 30-60 seconds
   - Remain within ±0.05 pH of a stable value
   - Typically takes 1-3 minutes in calibration buffer

**Tip:** Before running calibration, check that the current reading is close to the expected buffer value (within ~0.5 pH). If it's way off, your probe may need cleaning or the buffer may be contaminated.

#### Important: Probe Enable/Disable

**Do NOT disable the probe during calibration** - the probe must be enabled to provide readings for calibration. Only disable the probe if you need to stop any pH-based automation (like dosing pumps) during calibration.

#### Saltwater/Reef Systems

Use pH 7.0 (midpoint) and pH 10.0 (highpoint) calibration buffers:

1. **Place probe in pH 7.0 buffer** and wait for reading to stabilize (see monitoring section above)
2. **Run midpoint calibration** using `reef_pi.calibrate_ph_midpoint` with `expected: 7.0`
3. **Rinse probe** and place in pH 10.0 buffer, wait for reading to stabilize
4. **Run highpoint calibration** using `reef_pi.calibrate_ph_highpoint` with `expected: 10.0`

#### Freshwater Systems

Use pH 4.0 (midpoint) and pH 7.0 (highpoint) calibration buffers:

1. **Place probe in pH 4.0 buffer** and wait for reading to stabilize (see monitoring section above)
2. **Run midpoint calibration** using `reef_pi.calibrate_ph_midpoint` with `expected: 4.0`
3. **Rinse probe** and place in pH 7.0 buffer, wait for reading to stabilize
4. **Run highpoint calibration** using `reef_pi.calibrate_ph_highpoint` with `expected: 7.0`

### Example Service Calls

**Complete Saltwater Calibration:**
```yaml
# Step 1: Place probe in pH 7.0 buffer, wait to stabilize, then calibrate
service: reef_pi.calibrate_ph_midpoint
target:
  entity_id: sensor.reef_pi_ph
data:
  expected: 7.0

# Step 2: Rinse, place in pH 10.0 buffer, wait to stabilize, then calibrate
service: reef_pi.calibrate_ph_highpoint
target:
  entity_id: sensor.reef_pi_ph
data:
  expected: 10.0
```

**Complete Freshwater Calibration:**
```yaml
# Step 1: Place probe in pH 4.0 buffer, wait to stabilize, then calibrate
service: reef_pi.calibrate_ph_midpoint
target:
  entity_id: sensor.reef_pi_ph
data:
  expected: 4.0

# Step 2: Rinse, place in pH 7.0 buffer, wait to stabilize, then calibrate
service: reef_pi.calibrate_ph_highpoint
target:
  entity_id: sensor.reef_pi_ph
data:
  expected: 7.0
```

**Optional: Disable pH Automation During Calibration**

If you have pH-based automation (like dosing pumps) that you want to pause during calibration:
```yaml
# Before calibration: disable the probe's control functions
service: reef_pi.set_ph_probe_enabled
target:
  entity_id: sensor.reef_pi_ph
data:
  enabled: false

# ... perform calibration ...

# After calibration: re-enable
service: reef_pi.set_ph_probe_enabled
target:
  entity_id: sensor.reef_pi_ph
data:
  enabled: true
```

## NOTE: How to "fix" intermittent pH readings
On some installations of this addon, it can cause Reef Pi to intermittently drop the reading from both the Reef Pi graph/database and in Home Assistant.

To fix this, in Home Assistant go to Settings > Integrations > Reef-Pi integration and under "Integration entries" click on "Configure" and select "Disable pH sensor" and click on "Submit" and then click on the 3 vertical dots and select "Reload"

To bring in pH sensor readings into Home Assistant you will need to enable the MQTT functionality from within the Reef Pi systems interface.
