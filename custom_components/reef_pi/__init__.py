"""The ha_reef_pi integration."""

from __future__ import annotations

import asyncio
import html
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core_config import Config
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .async_api import CannotConnect, InvalidAuth, ReefApi
from .const import (
    _LOGGER,
    CALIBRATION_MODE,
    CALIBRATION_POINTS,
    CALIBRATION_PROBE,
    CALIBRATION_TYPE_FRESHWATER,
    CALIBRATION_TYPE_SALTWATER,
    CALIBRATION_WAIT_SECONDS,
    CONFIG_OPTIONS,
    DISABLE_PH,
    DOMAIN,
    HOST,
    MANUFACTURER,
    PASSWORD,
    START_CALIBRATION,
    UPDATE_INTERVAL_CFG,
    UPDATE_INTERVAL_MIN,
    USER,
    VERIFY_TLS,
)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS = ["sensor", "switch", "light", "binary_sensor", "button"]

SERVICE_CALIBRATE_PH = "calibrate_ph_probe"
CONF_CONFIG_ENTRY_ID = "config_entry_id"
CALIBRATION_NOTIFICATION_PREFIX = "reef_pi_calibration"
CALIBRATION_PROGRESS_STEP = 15

CALIBRATION_MODE_LABELS = {
    CALIBRATION_TYPE_FRESHWATER: "Freshwater",
    CALIBRATION_TYPE_SALTWATER: "Saltwater",
}

CALIBRATION_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required(CALIBRATION_PROBE): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Required(CALIBRATION_MODE): vol.In(
            [CALIBRATION_TYPE_FRESHWATER, CALIBRATION_TYPE_SALTWATER]
        ),
    }
)

REEFPI_DATETIME_FORMAT = "%b-%d-%H:%M, %Y"


CONFIG_SCHEMA = vol.Schema({DOMAIN: CONFIG_OPTIONS}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up configured."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ha_reef_pi from a config entry."""

    websession = async_get_clientsession(hass)
    coordinator = ReefPiDataUpdateCoordinator(hass, websession, entry)

    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    undo_listener = entry.add_update_listener(update_listener)

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "undo_update_listener": undo_listener,
    }

    async def _async_handle_calibration(service_call):
        probe_id = service_call.data[CALIBRATION_PROBE]
        mode = service_call.data[CALIBRATION_MODE]
        entry_id = service_call.data.get(CONF_CONFIG_ENTRY_ID)

        async def _match_coordinator() -> ReefPiDataUpdateCoordinator:
            candidates: list[ReefPiDataUpdateCoordinator] = []
            if entry_id:
                if entry_id not in hass.data[DOMAIN]:
                    raise HomeAssistantError(
                        f"No reef-pi configuration entry found for '{entry_id}'"
                    )
                candidates.append(hass.data[DOMAIN][entry_id]["coordinator"])
            else:
                candidates = [
                    data["coordinator"] for data in hass.data[DOMAIN].values()
                ]

            if not candidates:
                raise HomeAssistantError("No reef-pi coordinators are available")

            for candidate in candidates:
                try:
                    await candidate.async_refresh_ph_catalog()
                except CannotConnect as err:
                    raise HomeAssistantError("Unable to contact reef-pi API") from err
                if probe_id in candidate.ph_catalog:
                    return candidate

            if len(candidates) == 1:
                return candidates[0]

            raise HomeAssistantError(
                f"Unable to find probe {probe_id} on the selected reef-pi host"
            )

        target = await _match_coordinator()
        target.hass.async_create_task(target.async_calibrate_ph_probe(probe_id, mode))

    if not hass.services.has_service(DOMAIN, SERVICE_CALIBRATE_PH):
        hass.services.async_register(
            DOMAIN,
            SERVICE_CALIBRATE_PH,
            _async_handle_calibration,
            schema=CALIBRATION_SCHEMA,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    for component in PLATFORMS:
        await hass.config_entries.async_forward_entry_unload(entry, component)

    hass.data[DOMAIN][entry.entry_id]["undo_update_listener"]()
    hass.data[DOMAIN].pop(entry.entry_id)

    return True


async def update_listener(hass, config_entry):
    """Update listener."""
    await hass.config_entries.async_reload(config_entry.entry_id)


class ReefPiDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Reef-Pi data API."""

    def __init__(self, hass, session, config_entry):
        """Initialize."""

        _LOGGER.debug(
            "Using host %s for %s", config_entry.data[HOST], config_entry.title
        )
        self.default_name = config_entry.title
        self.username = config_entry.data[USER]
        self.password = config_entry.data[PASSWORD]
        self.api = ReefApi(
            config_entry.data[HOST], verify=config_entry.data[VERIFY_TLS]
        )
        self.configuration_url = config_entry.data[HOST]
        self.unique_id = config_entry.data[HOST]
        self.hass = hass

        self.update_interval = UPDATE_INTERVAL_MIN
        update_interval = config_entry.options.get(
            UPDATE_INTERVAL_CFG
        ) or config_entry.data.get(UPDATE_INTERVAL_CFG)
        if update_interval is not None:
            self.update_interval = timedelta(seconds=update_interval)

        self.disable_ph = config_entry.options.get(DISABLE_PH) or False

        self.has_temperature = False
        self.has_equipment = False
        self.has_ph_capability = False
        self.has_ph = False
        self.has_pumps = False
        self.has_ato = False
        self.has_timers = False
        self.has_lights = False
        self.has_camera = False
        self.has_macro = False
        self.has_display = False

        self.info = {}
        self.capabilities = {}
        self.tcs = {}
        self.equipment = {}
        self.ph = {}
        self.ph_catalog: dict[int, dict[str, Any]] = {}
        self.pumps = {}
        self.ato = {}
        self.ato_states = {}
        self.lights = {}
        self.inlets = {}
        self.macros = {}
        self.timers = {}
        self.display = {}

        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=self.update_interval
        )

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            configuration_url=self.configuration_url,
            identifiers={(DOMAIN, self.unique_id)},
            manufacturer=MANUFACTURER,
            model=self.info["model"] if self.info["model"] else "Reef PI",
            name=self.info["name"] if self.info["name"] else self.default_name,
            sw_version=self.info["name"] if self.info["name"] else None,
        )

    async def update_capabilities(self):
        _LOGGER.debug("Fetching capabilities")

        def get_capability(name):
            return name in self.capabilities.keys() and self.capabilities[name]

        self.capabilities = await self.api.capabilities()
        if self.capabilities:
            ph_capable = get_capability("ph")
            self.has_temperature = get_capability("temperature")
            self.has_equipment = get_capability("equipment")
            self.has_ph_capability = ph_capable
            self.has_ph = ph_capable and not self.disable_ph
            self.has_pumps = get_capability("doser")
            self.has_ato = get_capability("ato")
            self.has_timers = get_capability("timers")
            self.has_lights = get_capability("lighting")
            self.has_camera = get_capability("camera")
            self.has_macro = get_capability("macro")
            self.has_display = get_capability("display")
            _LOGGER.debug("Capabilities: ok")

    async def update_info(self):
        _LOGGER.debug("Fetching info")
        info = await self.api.info()
        if info:
            info["cpu_temperature"] = float(info["cpu_temperature"].split("'")[0])
            info["model"] = info["model"].rstrip("\0")
            info["capabilities"] = self.capabilities
            _LOGGER.debug("Basic info: ok")
            self.info = info
            _LOGGER.debug("Info: ok")

    async def update_temperature(self):
        if self.has_temperature:
            _LOGGER.debug("Fetching temperature")
            sensors = await self.api.temperature_sensors()
            if sensors:
                _LOGGER.debug("temperature updated: %d", len(sensors))
                all_tcs = {}
                for sensor in sensors:
                    all_tcs[sensor["id"]] = {
                        "name": sensor["name"],
                        "fahrenheit": sensor["fahrenheit"],
                        "temperature": (await self.api.temperature(sensor["id"]))[
                            "temperature"
                        ],
                        "attributes": sensor,
                    }
                self.tcs = all_tcs

    async def update_equipment(self):
        if self.has_equipment:
            _LOGGER.debug("Fetching equipment")
            equipment = await self.api.equipment()
            if equipment:
                _LOGGER.debug("equipment updated: %s", json.dumps(equipment))
                all_equipment = {}
                for device in equipment:
                    all_equipment[device["id"]] = {
                        "name": device["name"],
                        "state": device["on"],
                        "attributes": device,
                    }
                self.equipment = all_equipment

    async def update_timers(self):
        if self.has_timers:
            _LOGGER.debug("Fetching timers")
            timers = await self.api.timers()
            if timers:
                _LOGGER.debug("timers updated: %s", json.dumps(timers))
                all_timers = {}
                for timer in timers:
                    all_timers[timer["id"]] = {
                        "name": timer["name"],
                        "state": timer["enable"],
                        "attributes": timer,
                    }
                self.timers = all_timers

    async def update_macros(self):
        if self.has_macro:
            _LOGGER.debug("Fetching macros")
            macros = await self.api.macros()
            if macros:
                _LOGGER.debug("macros updated: %s", json.dumps(macros))
                all_macros = {}
                for macro in macros:
                    all_macros[macro["id"]] = {
                        "name": macro["name"],
                        "attributes": macro,
                    }
                self.macros = all_macros

    async def update_ph(self):
        if not self.has_ph_capability:
            return

        _LOGGER.debug("Fetching phprobes")
        probes = await self.api.phprobes()

        if not probes:
            self.ph = {}
            self.ph_catalog = {}
            return

        _LOGGER.debug("pH probes updated: %s", json.dumps(probes))
        catalog: dict[int, dict[str, Any]] = {}
        for probe in probes:
            probe_id_raw = probe.get("id")
            try:
                probe_id = int(probe_id_raw)
            except (TypeError, ValueError):
                _LOGGER.debug("Unable to coerce probe id %s to int", probe_id_raw)
                try:
                    probe_id = int(str(probe_id_raw))
                except (TypeError, ValueError):
                    continue

            catalog[probe_id] = {"name": probe.get("name", str(probe_id)), "attributes": probe}

        self.ph_catalog = catalog

        if not self.has_ph:
            self.ph = {}
            return

        all_ph: dict[str | int, dict[str, Any]] = {}
        for probe_id, catalog_entry in catalog.items():
            attributes = catalog_entry["attributes"]
            ph = await self.api.ph_readings(attributes["id"])
            value = round(ph["value"], 4) if ph["value"] else None

            all_ph[attributes["id"]] = {
                "name": catalog_entry["name"],
                "value": value,
                "attributes": attributes,
            }

        self.ph = all_ph
        _LOGGER.debug("Got %d pH probes: %s", len(all_ph), all_ph)

    async def update_lights(self):
        if self.has_lights:
            _LOGGER.debug("Fetching lights")
            lights = await self.api.lights()
            if lights:
                all_light = {}
                for light in lights:
                    for channel in list(light["channels"].keys()):
                        light_id = light["id"]
                        if light["channels"][channel]["manual"]:
                            id = f"{light_id}-{channel}"
                            light_name = light["name"]
                            channel_name = light["channels"][channel]["name"]

                            state = light["channels"][channel]["value"] > 0
                            all_light[id] = {
                                "name": f"{light_name}-{channel_name}",
                                "channel_id": channel,
                                "light_id": light_id,
                                "value": light["channels"][channel]["value"],
                                "state": state,
                                "attributes": light["channels"][channel],
                            }

        self.lights = all_light

    async def update_display(self):
        if self.has_display:
            _LOGGER.debug("Fetching display state")
            state = await self.api.display_state()
            if state:
                self.display = state

    async def async_refresh_ph_catalog(self) -> None:
        """Ensure the pH probe catalog is populated."""

        if not self.has_ph_capability:
            return

        if self.ph_catalog:
            return

        await self.update_ph()

    async def async_get_ph_probe_options(self) -> dict[str, str]:
        """Return probe options for UI selection."""

        await self.update_ph()
        if not self.ph_catalog:
            return {}

        return {
            str(probe_id): catalog["name"]
            for probe_id, catalog in sorted(
                self.ph_catalog.items(), key=lambda item: item[1]["name"].lower()
            )
        }

    async def async_calibrate_ph_probe(self, probe_id: int, mode: str) -> None:
        """Run a two point calibration for the provided probe."""

        if mode not in CALIBRATION_POINTS:
            self._async_create_popup_notification(
                notification_id=f"{CALIBRATION_NOTIFICATION_PREFIX}_{self.unique_id}_invalid_mode",
                title="reef-pi calibration",
                heading="Are you sure?",
                body=f"Unknown calibration mode: {mode}",
            )
            return

        await self.update_ph()
        probe = self.ph_catalog.get(probe_id)

        if not probe:
            self._async_create_popup_notification(
                notification_id=(
                    f"{CALIBRATION_NOTIFICATION_PREFIX}_{self.unique_id}_{probe_id}_missing"
                ),
                title="reef-pi calibration",
                heading="Are you sure?",
                body=(
                    f"pH probe {probe_id} could not be found. "
                    "Refresh the integration options and try again."
                ),
            )
            return

        probe_name = probe["name"]
        mode_name = CALIBRATION_MODE_LABELS.get(mode, mode.title())
        probe_identifier = probe["attributes"]["id"]

        async def _run_step(step: str, expected: float) -> bool:
            solution = "low" if step == "low" else "high"
            notification_id = (
                f"{CALIBRATION_NOTIFICATION_PREFIX}_{self.unique_id}_{probe_identifier}_{step}"
            )
            title = f"{probe_name}: {mode_name} {solution} point"
            instruction = (
                f"Place the probe in the {solution} calibration solution (pH {expected:.2f})."
            )

            remaining = CALIBRATION_WAIT_SECONDS
            latest_observed: float | None = None
            last_error: str | None = None
            while remaining > 0:
                value, error = await self._async_read_probe_value(probe_identifier)
                if value is not None:
                    latest_observed = value
                    last_error = None
                elif error:
                    last_error = error
                lines = [instruction, ""]
                if latest_observed is not None:
                    lines.append(f"Current probe reading: {latest_observed:.2f} pH.")
                else:
                    if last_error:
                        lines.append(last_error)
                    else:
                        lines.append("Current probe reading is unavailable.")
                lines.extend(
                    [
                        "",
                        "Time remaining before the reading is saved: "
                        f"{self._format_seconds(remaining)}.",
                    ]
                )
                message = "\n".join(lines)
                self._async_create_popup_notification(
                    notification_id=notification_id,
                    title=title,
                    heading="Are you sure?",
                    body=message,
                )
                interval = min(CALIBRATION_PROGRESS_STEP, remaining)
                await asyncio.sleep(interval)
                remaining -= interval

            self._async_create_popup_notification(
                notification_id=notification_id,
                title=title,
                heading="Calibration update",
                body="Capturing the probe reading...",
            )

            observed, error = await self._async_read_probe_value(probe_identifier)
            if observed is None:
                extra = ""
                if latest_observed is not None:
                    extra = (
                        " Last recorded reading before capture was "
                        f"{latest_observed:.2f} pH."
                    )
                if error:
                    extra = f" {error}"
                self._async_create_popup_notification(
                    notification_id=notification_id,
                    title=title,
                    heading="Calibration failed",
                    body=(
                        "The probe did not report a reading when the calibration point was "
                        f"captured.{extra}"
                    ),
                )
                return False

            try:
                success, rejection = await self.api.ph_probe_calibrate_point(
                    probe_identifier, expected, observed, step
                )
            except CannotConnect:
                self._async_create_popup_notification(
                    notification_id=notification_id,
                    title=title,
                    heading="Calibration failed",
                    body=(
                        "Home Assistant could not reach reef-pi while saving the "
                        "calibration point. Check the controller connection and try "
                        "again."
                    ),
                )
                return False
            except InvalidAuth:
                self._async_create_popup_notification(
                    notification_id=notification_id,
                    title=title,
                    heading="Calibration failed",
                    body=(
                        "reef-pi rejected Home Assistant's credentials while saving "
                        "this calibration point. Re-authenticate the integration and "
                        "retry."
                    ),
                )
                return False
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception(
                    "Unexpected error while saving %s calibration point for probe %s",
                    step,
                    probe_identifier,
                )
                self._async_create_popup_notification(
                    notification_id=notification_id,
                    title=title,
                    heading="Calibration failed",
                    body=(
                        "An unexpected error occurred while saving the calibration "
                        "point. Check the Home Assistant logs for details."
                    ),
                )
                return False

            if not success:
                detail = f" Observed reading was {observed:.2f} pH."
                message = (
                    "The reef-pi API rejected the calibration data. Please try again."
                    f"{detail}"
                )
                if rejection:
                    message = (
                        "reef-pi rejected the calibration data: "
                        f"{rejection.strip()}"
                        f"{detail}"
                    )
                self._async_create_popup_notification(
                    notification_id=notification_id,
                    title=title,
                    heading="Calibration failed",
                    body=message,
                )
                return False

            self._async_create_popup_notification(
                notification_id=notification_id,
                title=title,
                heading="Calibration saved",
                body=(
                    f"Calibration for the {solution} point saved "
                    f"(expected {expected:.2f}, observed {observed:.2f} pH)."
                ),
            )
            return True

        low_expected = CALIBRATION_POINTS[mode]["low"]
        high_expected = CALIBRATION_POINTS[mode]["high"]

        if not await _run_step("low", low_expected):
            return

        self._async_create_popup_notification(
            notification_id=(
                f"{CALIBRATION_NOTIFICATION_PREFIX}_{self.unique_id}_{probe_identifier}_instructions"
            ),
            title=f"{probe_name}: Prepare high point",
            heading="Are you sure?",
            body="Rinse the probe and place it in the high calibration solution to continue.",
        )

        if not await _run_step("high", high_expected):
            return

        self._async_create_popup_notification(
            notification_id=(
                f"{CALIBRATION_NOTIFICATION_PREFIX}_{self.unique_id}_{probe_identifier}_complete"
            ),
            title=f"{probe_name}: Calibration finished",
            heading="Calibration finished",
            body=f"Two point calibration for {probe_name} is complete.",
        )

        await self.async_request_refresh()

    async def _async_read_probe_value(
        self, probe_identifier: int
    ) -> tuple[float | None, str | None]:
        """Fetch the latest reading for a probe, handling API errors."""

        try:
            reading = await self.api.ph(probe_identifier)
        except CannotConnect:
            return None, "Unable to contact reef-pi to read the probe."
        except InvalidAuth:
            return None, "reef-pi authentication failed when reading the probe."
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception(
                "Unexpected error while reading probe %s", probe_identifier
            )
            return None, "An unexpected error occurred while reading the probe."

        value = reading.get("value") if reading else None
        if isinstance(value, (int, float)):
            return float(value), None

        return None, None

    @staticmethod
    def _format_seconds(seconds: int) -> str:
        minutes, secs = divmod(max(seconds, 0), 60)
        return f"{minutes:02}:{secs:02}"

    @staticmethod
    def _format_popup_message(heading: str, body: str) -> str:
        """Render calibration guidance inside a Lovelace-style popup card."""

        escaped_heading = html.escape(heading)
        escaped_body = html.escape(body).replace("\n", "<br>")
        return (
            f"<ha-card header=\"{escaped_heading}\">"
            f"<div class=\"card-content\">{escaped_body}</div>"
            "</ha-card>"
        )

    def _async_create_popup_notification(
        self,
        *,
        notification_id: str,
        title: str,
        heading: str,
        body: str,
    ) -> None:
        """Create a persistent notification styled like a Lovelace popup."""

        persistent_notification.async_create(
            self.hass,
            self._format_popup_message(heading, body),
            title=title,
            notification_id=notification_id,
        )

    async def update_inlets(self):
        if self.has_ato:
            _LOGGER.debug("Fetching inlets")
            inlets = await self.api.inlets()
            if inlets:
                _LOGGER.debug("inlets updated: %s", json.dumps(inlets))
                all_inlet = {}
                for inlet in inlets:
                    inlet_raw_value = await self.api.inlet(inlet["id"])

                    if inlet_raw_value == 1:
                        inlet_value = True
                    else:
                        inlet_value = False

                    all_inlet[inlet["id"]] = {
                        "name": inlet["name"],
                        "state": inlet_value,
                        "attributes": inlet,
                    }
                self.inlets = all_inlet

    async def update_pumps(self):
        if self.has_pumps:
            _LOGGER.debug("Fetching pumps")
            result = {}
            try:
                pumps = await self.api.pumps()
                for pump in pumps:
                    key = f"{pump['jack']}_{pump['pin']}"
                    _LOGGER.debug("Pump %s: %s", key, json.dumps(pump))
                    if key not in result.keys():
                        result[key] = {
                            "name": pump["name"],
                            "time": datetime.fromtimestamp(0),
                            "attributes": {pump["id"]: pump},
                        }
                    else:
                        result[key]["attributes"][pump["id"]] = pump

                    current = await self.api.pump(pump["id"])
                    if (
                        current
                        and "time" in current.keys()
                        and "pump" in current.keys()
                    ):
                        time = datetime.strptime(
                            current["time"], REEFPI_DATETIME_FORMAT
                        )
                        if time > result[key]["time"]:
                            result[key]["time"] = time
                            result[key]["attributes"]["duration"] = current["pump"]
            except Exception as ex:
                _LOGGER.exception(ex)
            self.pumps = result

    async def update_atos(self):
        if self.has_ato:
            atos = await self.api.atos()
            atos = {a["id"]: a for a in atos}
            ato_states = {}
            for id in atos.keys():
                ato_states[id] = {"ts": datetime.fromtimestamp(0), "pump": 0}
                states = await self.api.ato(id)
                ato_state = [s for s in states if s["pump"] != 0]
                if len(ato_state) > 0:
                    ato_states[id] = ato_state[-1]
                    ato_states[id]["ts"] = datetime.strptime(
                        ato_states[id]["time"], REEFPI_DATETIME_FORMAT
                    )
                else:
                    if len(states) > 0:
                        ato_states[id] = states[-1]
                        ato_states[id]["ts"] = datetime.strptime(
                            ato_states[id]["time"], REEFPI_DATETIME_FORMAT
                        )

            self.ato = atos
            self.ato_states = ato_states

    async def _async_update_data(self):
        """Update data via REST API."""
        try:
            if not self.api.is_authenticated():
                _LOGGER.debug("Authenticating")
                await self.api.authenticate(self.username, self.password)
                _LOGGER.debug("Authenticated")

            await self.update_capabilities()
            await self.update_info()
            await self.update_temperature()
            await self.update_equipment()
            await self.update_ph()
            await self.update_pumps()
            await self.update_atos()
            await self.update_inlets()
            await self.update_lights()
            await self.update_display()
            await self.update_macros()
            await self.update_timers()
        except InvalidAuth as error:
            raise ConfigEntryAuthFailed from error
        except CannotConnect as error:
            raise UpdateFailed(error) from error
        return {}

    async def equipment_control(self, id, state):
        await self.api.equipment_control(id, state)
        self.equipment[id]["state"] = state

    async def light_control(self, id, value):
        await self.api.light_update(
            self.lights[id]["light_id"], self.lights[id]["channel_id"], value
        )
        self.lights[id]["value"] = value
        if value > 0:
            self.lights[id]["state"] = True
        else:
            self.lights[id]["state"] = False

    async def ato_update(self, id, enable):
        await self.api.ato_update(id, enable)
        self.ato[id]["enable"] = enable

    async def run_script(self, id):
        await self.api.run_macro(id)

    async def reboot(self):
        await self.api.reboot()

    async def power_off(self):
        await self.api.power_off()

    async def display_switch(self, on: bool):
        await self.api.display_switch(on)
        self.display["on"] = on

    async def display_brightness(self, value: int):
        await self.api.display_brightness(value)
        self.display["brightness"] = value


    async def timer_control(self, id, state):
        await self.api.timer_control(id, state)
        self.timers[id]["state"] = state
