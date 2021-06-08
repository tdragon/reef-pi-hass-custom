"""Constants for the ha_reef_pi integration."""

import logging
from datetime import timedelta

DOMAIN = "reef_pi"

HOST = "host"
USER = "username"
PASSWORD = "password"
VERIFY_TLS = "verify"
UPDATE_INTERVAL_MIN = timedelta(minutes=1)
TIMEOUT_API_SEC = 5

_LOGGER = logging.getLogger(__package__)
