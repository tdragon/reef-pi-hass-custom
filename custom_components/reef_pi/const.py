"""Constants for the ha_reef_pi integration."""

import logging
from datetime import timedelta

DOMAIN = "reef_pi"
MANUFACTURER = "reef-pi.github.io"

HOST = "host"
USER = "username"
PASSWORD = "password"
VERIFY_TLS = "verify"
UPDATE_INTERVAL_MIN = timedelta(minutes=1)
TIMEOUT_API_SEC = 1

_LOGGER = logging.getLogger(__package__)
