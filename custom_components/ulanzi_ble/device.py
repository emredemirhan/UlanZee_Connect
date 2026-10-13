"""BLE connection handling for Ulanzi lights."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
import contextlib
from datetime import datetime
import logging

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import (
    BLEAK_RETRY_EXCEPTIONS,
    BleakClientWithServiceCache,
    establish_connection,
)

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later

from .const import (
    COMMAND_DELAY,
    CONNECT_ATTEMPTS,
    DOMAIN,
    IDLE_DISCONNECT_SECONDS,
    NOTIFY_CHAR_UUID,
    NOTIFY_SETTLE_DELAY,
    RETRY_DELAY,
    SEND_ATTEMPTS,
    WRITE_CHAR_UUID,
)
from .protocol import is_ulanzi_name

_LOGGER = logging.getLogger(__name__)

_RETRY_EXCEPTIONS = (BleakError, TimeoutError, *BLEAK_RETRY_EXCEPTIONS)


class UlanziError(Exception):
    """Sending a command to the light failed."""


class UlanziNotFoundError(UlanziError):
    """The light is not visible to any Bluetooth adapter or proxy."""


class UlanziDevice:
    """Keeps one BLE connection to a light and serialises commands over it.

    The connection is opened on the first command, kept open, and closed after
    IDLE_DISCONNECT_SECONDS without commands. If it drops, the next command
    reconnects.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self._lock = asyncio.Lock()
        self._client: BleakClientWithServiceCache | None = None
        self._cancel_idle: CALLBACK_TYPE | None = None
        self._expected_disconnect = False

    @property
    def address(self) -> str:
        return self._entry.data[CONF_ADDRESS]

    @property
    def advertised_name(self) -> str | None:
        return self._entry.data.get(CONF_NAME) or None

    @property
    def name(self) -> str:
        return self.advertised_name or self._entry.title

    async def async_send(self, commands: Sequence[bytes]) -> None:
        """Send packets in order, reconnecting if needed."""
        async with self._lock:
            self._cancel_idle_timer()
            try:
                await self._async_send_locked(commands)
            finally:
                self._schedule_idle_disconnect()

    async def async_shutdown(self) -> None:
        """Close the connection; called when the entry unloads."""
        self._cancel_idle_timer()
        async with self._lock:
            await self._async_disconnect_locked()

    async def _async_send_locked(self, commands: Sequence[bytes]) -> None:
        last_error: Exception | None = None
        for attempt in range(1, SEND_ATTEMPTS + 1):
            try:
                client = await self._async_ensure_connected()
                for command in commands:
                    _LOGGER.debug("%s: write %s", self.name, command.hex(" "))
                    await client.write_gatt_char(
                        WRITE_CHAR_UUID, command, response=False
                    )
                    await asyncio.sleep(COMMAND_DELAY)
                return
            except UlanziNotFoundError as err:
                last_error = err
            except _RETRY_EXCEPTIONS as err:
                last_error = err
                _LOGGER.debug(
                    "%s: attempt %d/%d failed: %s",
                    self.name,
                    attempt,
                    SEND_ATTEMPTS,
                    err,
                )
                await self._async_disconnect_locked()
            if attempt < SEND_ATTEMPTS:
                await asyncio.sleep(RETRY_DELAY)

        if isinstance(last_error, UlanziNotFoundError):
            raise last_error
        raise UlanziError(str(last_error) or type(last_error).__name__) from last_error

    async def _async_ensure_connected(self) -> BleakClientWithServiceCache:
        if self._client is not None and self._client.is_connected:
            return self._client

        ble_device = self._async_find_ble_device()
        if ble_device is None:
            raise UlanziNotFoundError(
                f"{self.name} ({self.address}) is not in Bluetooth range"
            )

        _LOGGER.debug("%s: connecting to %s", self.name, ble_device.address)
        self._expected_disconnect = False
        client = await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            self.name,
            disconnected_callback=self._on_disconnected,
            max_attempts=CONNECT_ATTEMPTS,
            ble_device_callback=lambda: self._async_find_ble_device() or ble_device,
        )
        try:
            # The light misbehaves unless something is subscribed to FFF1.
            await client.start_notify(NOTIFY_CHAR_UUID, self._on_notification)
        except _RETRY_EXCEPTIONS:
            self._expected_disconnect = True
            with contextlib.suppress(*_RETRY_EXCEPTIONS):
                await client.disconnect()
            raise
        await asyncio.sleep(NOTIFY_SETTLE_DELAY)
        self._client = client
        return client

    @callback
    def _async_find_ble_device(self) -> BLEDevice | None:
        """Find the light by address, falling back to its advertised name."""
        if ble_device := bluetooth.async_ble_device_from_address(
            self._hass, self.address, connectable=True
        ):
            if self.advertised_name is None:
                self._async_learn_name()
            return ble_device

        # The light may use a rotating (private) address: look for the same
        # name under an address that no other entry of ours owns.
        if (name := self.advertised_name) is None:
            return None
        taken = {
            entry.unique_id
            for entry in self._hass.config_entries.async_entries(DOMAIN)
            if entry.entry_id != self._entry.entry_id
        }
        candidates = [
            info
            for info in bluetooth.async_discovered_service_info(
                self._hass, connectable=True
            )
            if info.name == name and info.address not in taken
        ]
        if not candidates:
            return None
        best = max(candidates, key=lambda info: info.rssi)
        _LOGGER.info(
            "%s: address changed from %s to %s", name, self.address, best.address
        )
        self._hass.config_entries.async_update_entry(
            self._entry,
            unique_id=best.address,
            data={**self._entry.data, CONF_ADDRESS: best.address},
        )
        return best.device

    @callback
    def _async_learn_name(self) -> None:
        """Store the advertised name so the light can be found if it moves."""
        info = bluetooth.async_last_service_info(
            self._hass, self.address, connectable=True
        )
        if info is not None and is_ulanzi_name(info.name):
            self._hass.config_entries.async_update_entry(
                self._entry, data={**self._entry.data, CONF_NAME: info.name}
            )

    @callback
    def _on_disconnected(self, client: BleakClient) -> None:
        if client is not self._client and self._client is not None:
            return
        self._client = None
        if not self._expected_disconnect:
            _LOGGER.debug("%s: disconnected unexpectedly", self.name)

    @callback
    def _on_notification(
        self, _char: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        _LOGGER.debug("%s: notify %s", self.name, data.hex(" "))

    async def _async_disconnect_locked(self) -> None:
        client, self._client = self._client, None
        if client is None:
            return
        self._expected_disconnect = True
        _LOGGER.debug("%s: disconnecting", self.name)
        if client.is_connected:
            with contextlib.suppress(*_RETRY_EXCEPTIONS):
                await client.stop_notify(NOTIFY_CHAR_UUID)
        with contextlib.suppress(*_RETRY_EXCEPTIONS):
            await client.disconnect()

    @callback
    def _schedule_idle_disconnect(self) -> None:
        self._cancel_idle_timer()
        self._cancel_idle = async_call_later(
            self._hass, IDLE_DISCONNECT_SECONDS, self._async_idle_disconnect
        )

    @callback
    def _cancel_idle_timer(self) -> None:
        if self._cancel_idle is not None:
            self._cancel_idle()
            self._cancel_idle = None

    async def _async_idle_disconnect(self, _now: datetime) -> None:
        self._cancel_idle = None
        async with self._lock:
            # A command ran while we waited for the lock and re-armed the timer.
            if self._cancel_idle is not None:
                return
            await self._async_disconnect_locked()
