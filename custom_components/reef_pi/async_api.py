"""Reef Pi api wrapper"""

import logging
from datetime import datetime
from typing import Any, Dict

import httpx

REEFPI_DATETIME_FORMAT = "%b-%d-%H:%M, %Y"
logger = logging.getLogger(__name__)


class ReefApi:
    def __init__(self, host, verify=False, timeout_sec=15):
        self.host = host
        self.verify = verify
        self.cookies = {}
        self.timeout = timeout_sec

        if not verify:
            import urllib3

            urllib3.disable_warnings()

    def is_authenticated(self):
        return self.cookies != {}

    async def authenticate(self, user, password):
        try:
            async with httpx.AsyncClient(verify=self.verify) as client:
                auth = {"user": user, "password": password}
                url = f"{self.host}/auth/signin"
                response = await client.post(url, json=auth, timeout=self.timeout)

                if response.status_code == 200:
                    self.cookies = {"auth": response.cookies["auth"]}
        except httpx.HTTPError as exc:
            raise CannotConnect from exc

        if response.status_code != 200:
            raise InvalidAuth

    async def _get(self, api) -> Any:
        if not self.is_authenticated():
            raise InvalidAuth

        try:
            async with httpx.AsyncClient(verify=self.verify) as client:
                url = f"{self.host}/api/{api}"
                client.cookies = self.cookies
                response = await client.get(url, timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise CannotConnect from exc

        if response.status_code != 200:
            return {}
        return response.json()

    async def _post(self, api, payload) -> bool:
        if not self.is_authenticated():
            raise InvalidAuth

        try:
            async with httpx.AsyncClient(verify=self.verify) as client:
                url = f"{self.host}/api/{api}"
                client.cookies = self.cookies
                response = await client.post(url, json=payload, timeout=self.timeout)
                return response.is_success
        except httpx.HTTPError as exc:
            raise CannotConnect from exc

    async def equipment(self, id=None):
        if id:
            return await self._get(f"equipment/{id}")
        return await self._get("equipment")

    async def equipment_control(self, id, state):
        payload = {"on": state}
        return await self._post(f"equipment/{id}/control", payload)

    async def temperature_sensors(self):
        return await self._get("tcs")

    async def temperature(self, id):
        return await self._get(f"tcs/{id}/current_reading")

    async def capabilities(self):
        return await self._get("capabilities")

    async def errors(self):
        return await self._get("errors")

    async def info(self):
        return await self._get("info")

    async def phprobes(self):
        return await self._get("phprobes")

    async def ph_readings(self, id: int):
        def get_time(x: dict[str, str]):
            try:
                return datetime.strptime(x["time"], REEFPI_DATETIME_FORMAT)
            except Exception as e:
                logger.error(f"Error parsing time: {e}")
                return datetime(1900, 1, 1)

        def get_latest_value(x: list[dict[str, str]] | None):
            if not x:
                return {"value": None}
            latest = sorted(x, key=get_time)[-1].get("value")
            return {"value": float(latest) if latest else None}

        readings = await self._get(f"phprobes/{id}/readings")
        return get_latest_value(readings.get("current"))

    async def ph(self, id):
        try:
            value = await self._get(f"phprobes/{id}/read")
            if value:
                return {"value": float(value)}
        except Exception:
            pass
        return {"value": None}

    async def pumps(self):
        return await self._get("doser/pumps")

    async def lights(self):
        return await self._get("lights")

    async def timers(self):
        return await self._get("timers")

    async def timer_control(self, id, state):
        payload = await self._get(f"timers/{id}")
        payload["enable"] = state
        return await self._post(f"timers/{id}", payload)

    async def inlets(self):
        return await self._get("inlets")

    async def inlet(self, id):
        try:
            async with httpx.AsyncClient(verify=self.verify) as client:
                url = f"{self.host}/api/inlets/{id}/read"
                client.cookies = self.cookies
                response = await client.post(url, json={}, timeout=self.timeout)
                if response.status_code != 200:
                    return {}
                return response.json()
        except httpx.HTTPError as exc:
            raise CannotConnect from exc

    async def light(self, id):
        return await self._get(f"lights/{id}")

    async def pump(self, id) -> Dict[str, str]:
        readings = await self._get(f"doser/pumps/{id}/usage")
        if readings and "current" in readings.keys() and len(readings["current"]):
            return readings["current"][-1]
        if readings and "historical" in readings.keys() and len(readings["historical"]):
            return readings["historical"][-1]
        return {}

    async def atos(self):
        return await self._get("atos")

    async def ato(self, id):
        readings = await self._get(f"atos/{id}/usage")
        if readings and "current" in readings.keys() and len(readings["current"]):
            return readings["current"]
        if readings and "historical" in readings.keys() and len(readings["historical"]):
            return readings["historical"]
        return []

    async def ato_update(self, id, enable):
        payload = await self._get(f"atos/{id}")
        payload["enable"] = enable
        return await self._post(f"atos/{id}", payload)

    async def light_update(self, id, channel_id, value):
        payload = await self._get(f"lights/{id}")
        payload["channels"][channel_id]["value"] = value
        return await self._post(f"lights/{id}", payload)

    async def macros(self):
        return await self._get("macros")

    async def run_macro(self, id):
        return await self._post(f"macros/{id}/run", "")

    async def reboot(self) -> bool:
        return await self._post("admin/reboot", {})

    async def power_off(self) -> bool:
        return await self._post("admin/poweroff", {})

    async def display_state(self) -> Dict[str, Any]:
        return await self._get("display")

    async def display_switch(self, on: bool) -> bool:
        action = "on" if on else "off"
        return await self._post(f"display/{action}", {})

    async def display_brightness(self, value: int) -> bool:
        payload = {"brightness": value}
        return await self._post("display", payload)

    async def ph_probe_calibrate(
        self, id: int, measurements: list[dict[str, float]]
    ) -> bool:
        return await self._post(f"phprobes/{id}/calibrate", measurements)

    async def ph_probe_calibrate_point(
        self, id: int, expected: float, observed: float, type_: str | None = None
    ) -> bool:
        payload = {"expected": expected, "observed": observed}
        if type_:
            payload["type"] = type_
        return await self._post(f"phprobes/{id}/calibratepoint", payload)


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


class ApiError(Exception):
    """Unexpected API result"""
