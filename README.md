[![Community Forum](https://img.shields.io/badge/Community-Forum-41BDF5.svg?style=popout)](https://community.home-assistant.io/t/reef-pi-home-assistant-integration/312945)

# Home Assistane Reef Pi integration

This custom integration provides a way to sensors data and control equipment connected to [Reef-Pi (An open source reef tank controller based on Raspberry Pi)](http://reef-pi.github.io/).

## Installation

### Manual
To install this integration manually you have to download the content of this repository to `config/custom_components/reef-pi-hass-custom` directory:
```bash
mkdir -p custom_components
cd custom_components
wget https://github.com/tdragon/reef-pi-hass-custom/archive/refs/heads/master.zip
unzip master.zip
rm master.zip
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



