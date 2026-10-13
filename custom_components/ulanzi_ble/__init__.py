"""Ulanzi BLE light integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .device import UlanziDevice

PLATFORMS: list[Platform] = [Platform.LIGHT]

UlanziConfigEntry = ConfigEntry[UlanziDevice]


async def async_setup_entry(hass: HomeAssistant, entry: UlanziConfigEntry) -> bool:
    """Set up a light from a config entry.

    No connection is made here: the light connects on its first command, so
    setup succeeds even while the light is switched off or out of range.
    """
    entry.runtime_data = UlanziDevice(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: UlanziConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_shutdown()
    return unload_ok
