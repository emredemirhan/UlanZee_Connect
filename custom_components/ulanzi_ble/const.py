"""Constants for the Ulanzi BLE integration."""

from __future__ import annotations

from .protocol import MAX_KELVIN, MIN_KELVIN  # noqa: F401

DOMAIN = "ulanzi_ble"
DEFAULT_NAME = "Ulanzi Light"
MANUFACTURER = "Ulanzi"

SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
WRITE_CHAR_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"

# Pause after each write; the light drops packets that arrive too fast.
COMMAND_DELAY = 0.05
# Pause after subscribing to notifications before the first write.
NOTIFY_SETTLE_DELAY = 0.2
# Close the BLE connection after this many idle seconds.
IDLE_DISCONNECT_SECONDS = 60
# establish_connection attempts per connect.
CONNECT_ATTEMPTS = 3
# Full connect+write attempts per command batch (covers stale connections).
SEND_ATTEMPTS = 2
RETRY_DELAY = 1.0
