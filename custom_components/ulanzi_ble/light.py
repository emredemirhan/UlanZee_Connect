"""Light entity for Ulanzi BLE lights."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    EFFECT_OFF,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import ExtraStoredData, RestoredExtraData, RestoreEntity

from . import UlanziConfigEntry
from . import protocol
from .const import DOMAIN, MANUFACTURER, MAX_KELVIN, MIN_KELVIN
from .device import UlanziDevice, UlanziError, UlanziNotFoundError

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: UlanziConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the light entity."""
    async_add_entities([UlanziLight(entry)])


class UlanziLight(LightEntity, RestoreEntity):
    """A two-tone (warm/cool white) Ulanzi light.

    The light cannot report its state, so the entity keeps an assumed state
    and restores it across restarts.
    """

    _attr_has_entity_name = True
    _attr_name = None
    _attr_translation_key = "light"
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_color_mode = ColorMode.COLOR_TEMP
    _attr_supported_color_modes = {ColorMode.COLOR_TEMP}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_min_color_temp_kelvin = MIN_KELVIN
    _attr_max_color_temp_kelvin = MAX_KELVIN
    _attr_effect_list = [EFFECT_OFF, *protocol.EFFECTS]

    def __init__(self, entry: UlanziConfigEntry) -> None:
        self._device: UlanziDevice = entry.runtime_data
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
        )
        self._attr_is_on = False
        self._attr_brightness = None
        self._attr_color_temp_kelvin = None
        self._attr_effect = EFFECT_OFF

    async def async_added_to_hass(self) -> None:
        """Restore the last known state."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == STATE_ON
        # Extra data is kept even while off, unlike the state attributes.
        if (extra := await self.async_get_last_extra_data()) is not None:
            data = extra.as_dict()
            if (brightness := data.get(ATTR_BRIGHTNESS)) is not None:
                self._attr_brightness = int(brightness)
            if (kelvin := data.get(ATTR_COLOR_TEMP_KELVIN)) is not None:
                self._attr_color_temp_kelvin = protocol.clamp_kelvin(kelvin)
            effect = data.get(ATTR_EFFECT)
            if self._attr_is_on and effect in protocol.EFFECTS:
                self._attr_effect = effect

    @property
    def extra_restore_state_data(self) -> ExtraStoredData:
        return RestoredExtraData(
            {
                ATTR_BRIGHTNESS: self._attr_brightness,
                ATTR_COLOR_TEMP_KELVIN: self._attr_color_temp_kelvin,
                ATTR_EFFECT: self._attr_effect,
            }
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on, then apply brightness, colour temperature and effect."""
        brightness: int | None = kwargs.get(ATTR_BRIGHTNESS)
        kelvin: int | None = kwargs.get(ATTR_COLOR_TEMP_KELVIN)
        effect: str | None = kwargs.get(ATTR_EFFECT)
        if effect is not None and effect != EFFECT_OFF and effect not in protocol.EFFECTS:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_effect",
                translation_placeholders={"effect": effect},
            )

        # "On" also ends a running effect, so the effect packet goes last.
        commands = [protocol.power_on()]
        if brightness is not None:
            commands.append(
                protocol.brightness(protocol.ha_brightness_to_level(brightness))
            )
        if kelvin is not None:
            kelvin = protocol.clamp_kelvin(kelvin)
            commands.append(protocol.color_temp(kelvin))
        if effect is not None and effect != EFFECT_OFF:
            commands.append(protocol.effect(effect))

        await self._async_send(commands)

        self._attr_is_on = True
        if brightness is not None:
            self._attr_brightness = brightness
        if kelvin is not None:
            self._attr_color_temp_kelvin = kelvin
        self._attr_effect = effect if effect is not None else EFFECT_OFF
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off. Brightness is never sent here: it would switch the light back on."""
        await self._async_send(protocol.power_off())
        self._attr_is_on = False
        self._attr_effect = EFFECT_OFF
        self.async_write_ha_state()

    async def _async_send(self, commands: list[bytes]) -> None:
        try:
            await self._device.async_send(commands)
        except UlanziNotFoundError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="not_found",
                translation_placeholders={"name": self._device.name},
            ) from err
        except UlanziError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="send_failed",
                translation_placeholders={
                    "name": self._device.name,
                    "error": str(err),
                },
            ) from err
