"""Constants for the ha_reef_pi integration."""

import logging
from datetime import timedelta

import voluptuous as vol

DOMAIN = "reef_pi"
MANUFACTURER = "reef-pi.github.io"

HOST = "host"
USER = "username"
PASSWORD = "password"
VERIFY_TLS = "verify"
UPDATE_INTERVAL_CFG = "update_interval"
DISABLE_PH = "disable_ph"
UPDATE_INTERVAL_MIN = timedelta(minutes=1)
TIMEOUT_API_SEC = 1

CONFIG_OPTIONS = {
    vol.Required(HOST, default="https://127.0.0.1"): str,  # type: ignore
    vol.Required(USER, default="reef-pi"): str,  # type: ignore
    vol.Required(PASSWORD, default=""): str,  # type: ignore
    vol.Optional(VERIFY_TLS, default=False): bool,  # type: ignore
    vol.Optional(
        UPDATE_INTERVAL_CFG,
        default=UPDATE_INTERVAL_MIN.total_seconds(),  # type: ignore
    ): int,
}

_LOGGER = logging.getLogger(__package__)
