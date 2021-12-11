"""Reef Pi api wrapper """

import requests
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

    def authenticate(self, user, password):
        try:
            auth = {"user": user, "password": password}
            url = f"{self.host}/auth/signin"
            response = requests.post(
                url, json=auth, verify=self.verify, timeout=self.timeout
            )
            if response.ok:
                self.cookies = {"auth": response.cookies["auth"]}
        except (ConnectionError, requests.exceptions.SSLError) as exc:
            raise CannotConnect from exc

        if not response.ok:
            raise InvalidAuth

    def _get(self, api) -> dict:
        if not self.is_authenticated():
            raise InvalidAuth

        try:
            url = f"{self.host}/api/{api}"
            response = requests.get(
                url, cookies=self.cookies, verify=self.verify, timeout=self.timeout
            )
        except ConnectionError as exc:
            raise CannotConnect from exc

        if not response.ok:
            return {}
        return json.loads(response.text)

    def _post(self, api, payload) -> dict:
        if not self.is_authenticated():
            raise InvalidAuth

        try:
            url = f"{self.host}/api/{api}"
            response = requests.post(
                url,
                json=payload,
                cookies=self.cookies,
                verify=self.verify,
                timeout=self.timeout,
            )
            return response.ok
        except ConnectionError as exc:
            raise CannotConnect from exc

    def equipment(self, id=None):
        if id:
            return self._get(f"equipment/{id}")
        return self._get("equipment")

    def equipment_control(self, id, on):
        payload = {"on": on}
        return self._post(f"equipment/{id}/control", payload)

    def temperature_sensors(self):
        return self._get("tcs")

    def temperature(self, id):
        return self._get(f"tcs/{id}/current_reading")

    def capabilities(self):
        return self._get("capabilities")

    def errors(self):
        return self._get("errors")

    def info(self):
        return self._get("info")

    def phprobes(self):
        return self._get("phprobes")

    def ph(self, id):
        readings = self._get(f"phprobes/{id}/readings")
        if readings and 'current' in readings.keys() and len(readings['current']):
            return readings['current'][-1]
        if readings and 'historical' in readings.keys() and len(readings['historical']):
            return readings['historical'][-1]
        return {'value': None}

    def pumps(self):
        return self._get("doser/pumps")

    def pump(self, id):
        readings = self._get(f"doser/pumps/{id}/usage")
        if readings and "current" in readings.keys() and len(readings['current']):
            return readings['current'][-1]
        if readings and "historical" in readings.keys() and len(readings['historical']):
            return readings['historical'][-1]
        return None


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


class ApiError(Exception):
    """Unexpected API result"""
