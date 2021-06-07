"""Reef Pi api wrapper """

import requests
import json

from homeassistant.exceptions import HomeAssistantError


class ReefApi:
    def __init__(self, host, verify=False, timeout_sec=5):
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
        except (ConnectionError, requests.exceptions.SSLError) as e:
            raise CannotConnect

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
        except ConnectionError:
            raise CannotConnect

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
        except ConnectionError:
            raise CannotConnect

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


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class ApiError(HomeAssistantError):
    """Unexpected API result"""
