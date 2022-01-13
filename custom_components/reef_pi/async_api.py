"""Reef Pi api wrapper """

import asyncio
import httpx
import json

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

    async def _get(self, api) -> dict:
        if not self.is_authenticated():
            raise InvalidAuth

        try:
            async with httpx.AsyncClient(verify=self.verify) as client:
                url = f"{self.host}/api/{api}"
                response = await client.get(url, cookies=self.cookies, timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise CannotConnect from exc

        if not response.status_code == 200:
            return {}
        return json.loads(response.text)

    async def _post(self, api, payload) -> dict:
        if not self.is_authenticated():
            raise InvalidAuth

        try:
            async with httpx.AsyncClient(verify=self.verify) as client:
                url = f"{self.host}/api/{api}"
                response = await client.post(url, json=payload, cookies=self.cookies, timeout=self.timeout)
            return response.status_code == 200
        except httpx.HTTPError as exc:
            raise CannotConnect from exc

    async def equipment(self, id=None):
        if id:
            return await self._get(f"equipment/{id}")
        return await self._get("equipment")

    async def equipment_control(self, id, on):
        payload = {"on": on}
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

    async def ph(self, id):
        readings = await self._get(f"phprobes/{id}/readings")
        if readings and 'current' in readings.keys() and len(readings['current']):
            return readings['current'][-1]
        if readings and 'historical' in readings.keys() and len(readings['historical']):
            return readings['historical'][-1]
        return {'value': None}

    async def pumps(self):
        return await self._get("doser/pumps")

    async def pump(self, id):
        readings = await self._get(f"doser/pumps/{id}/usage")
        if readings and "current" in readings.keys() and len(readings['current']):
            return readings['current'][-1]
        if readings and "historical" in readings.keys() and len(readings['historical']):
            return readings['historical'][-1]
        return None

    async def atos(self):
        return await self._get("atos")

    async def ato(self, id):
        readings = await self._get(f"atos/{id}/usage")
        if readings and "current" in readings.keys() and len(readings['current']):
            return readings['current']
        if readings and "historical" in readings.keys() and len(readings['historical']):
            return readings['historical']
        return None

    async def ato_update(self, id, enable):
        payload = await self._get(f"atos/{id}")
        payload["id"] = id
        payload["enable"] = enable
        return await self._post(f"atos/{id}", payload)


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


class ApiError(Exception):
    """Unexpected API result"""
