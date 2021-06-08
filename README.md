[![Community Forum](https://img.shields.io/badge/Community-Forum-41BDF5.svg?style=popout)](https://community.home-assistant.io/t/reef-pi-home-assistant-integration/312945)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
![GitHub All Releases](https://img.shields.io/github/downloads/tdragon/reef-pi-hass-custom/total)

# Home Assistane Reef Pi integration

This custom integration provides a way to sensors data and control equipment connected to [Reef-Pi (An open source reef tank controller based on Raspberry Pi)](http://reef-pi.github.io/).

## Installation

### Using [HACS](https://hacs.xyz/) (recommended)

This integration can be installed using HACS.
To do it add custom *integration* repository using url: `https://github.com/tdragon/reef-pi-hass-custom/`.
Then search for Reef Pi in *Integrations* section.

### Manual
To install this integration manually you have to download the content of this repository to `config/custom_components/reef-pi-hass-custom` directory:
```bash
mkdir -p custom_components/reef_pi
cd custom_components/reef_pi
wget https://github.com/tdragon/reef-pi-hass-custom/releases/download/0.1.2/reef_pi.zip
unzip reef_pi.zip
rm reef_pi.zip
```
After that rastrt Home Assistant.

## Configuration
Install integration from UI (Configuration --> Intergations --> + --> Search for `reef pi`)
Configuration options:
- Host (http://ip.address or https://ip.address)
- user name
- password
  
## Usage
Integration creates temperature sensor for each sensor connected to Reef PI: `sensor.temperature_sensor_name`
Additionaly it create one sensor for CPU temperature: `sensor.reef_pi_name`

For each equipment configured in Reef Pi an outlet entity is created: `switch.equipment_name`



