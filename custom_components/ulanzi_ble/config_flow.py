"""Config flow for Ulanzi BLE lights."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_address_present,
    async_discovered_service_info,
    async_last_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_NAME

from .const import DEFAULT_NAME, DOMAIN, SERVICE_UUID
from .protocol import is_ulanzi_name

_MAC_RE = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")

MANUAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ADDRESS): str,
        vol.Optional(CONF_NAME): str,
    }
)


def _normalize_mac(value: str) -> str:
    return value.strip().upper().replace("-", ":")


class UlanziConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ulanzi BLE lights."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a light found by Home Assistant's Bluetooth discovery."""
        # The FFF0 service is used by many cheap BLE gadgets; only offer
        # devices that actually call themselves Ulanzi.
        if not is_ulanzi_name(discovery_info.name):
            return self.async_abort(reason="not_supported")

        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        if self._async_update_moved_entry(discovery_info):
            return self.async_abort(reason="already_configured")

        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm adding a discovered light."""
        assert self._discovery_info is not None
        name = self._discovery_info.name
        if user_input is not None:
            return self._async_create(self._discovery_info.address, name)

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm", description_placeholders={"name": name}
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick one of the Ulanzi lights currently in range."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self._async_create(address, self._discovered[address].name)

        current_addresses = self._async_current_ids(include_ignore=False)
        for info in async_discovered_service_info(self.hass, connectable=True):
            if info.address in current_addresses or info.address in self._discovered:
                continue
            if is_ulanzi_name(info.name) or SERVICE_UUID in info.service_uuids:
                self._discovered[info.address] = info

        if not self._discovered:
            return await self.async_step_manual()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        {
                            address: f"{info.name} ({address})"
                            for address, info in self._discovered.items()
                        }
                    )
                }
            ),
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Enter the light's MAC address by hand."""
        errors: dict[str, str] = {}
        if user_input is not None:
            address = _normalize_mac(user_input[CONF_ADDRESS])
            if not _MAC_RE.match(address):
                errors[CONF_ADDRESS] = "invalid_address"
            else:
                await self.async_set_unique_id(address, raise_on_progress=False)
                self._abort_if_unique_id_configured()
                name = (user_input.get(CONF_NAME) or "").strip()
                if not name and (
                    info := async_last_service_info(
                        self.hass, address, connectable=True
                    )
                ):
                    name = info.name if is_ulanzi_name(info.name) else ""
                return self._async_create(address, name or None)

        return self.async_show_form(
            step_id="manual",
            data_schema=self.add_suggested_values_to_schema(MANUAL_SCHEMA, user_input),
            errors=errors,
        )

    def _async_create(self, address: str, name: str | None) -> ConfigFlowResult:
        return self.async_create_entry(
            title=name or DEFAULT_NAME,
            data={CONF_ADDRESS: address, CONF_NAME: name},
        )

    def _async_update_moved_entry(self, info: BluetoothServiceInfoBleak) -> bool:
        """If a configured light with this name vanished from its old address,
        assume it now uses this address and update the entry instead."""
        for entry in self._async_current_entries(include_ignore=False):
            if entry.data.get(CONF_NAME) != info.name:
                continue
            old_address = entry.data[CONF_ADDRESS]
            if old_address == info.address or async_address_present(
                self.hass, old_address, connectable=True
            ):
                continue
            self.hass.config_entries.async_update_entry(
                entry,
                unique_id=info.address,
                data={**entry.data, CONF_ADDRESS: info.address},
            )
            return True
        return False
