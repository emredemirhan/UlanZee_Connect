"""Byte-level protocol for Ulanzi BLE lights (e.g. EC65).

This module deliberately has no Home Assistant imports so it can be unit tested
on its own. Protocol reference: github.com/kevinlouie/lctl (ble_controller.py).

Every packet is 6 or 7 bytes framed as ``FF <cmd> <len> <payload...> AA``.
"""

from __future__ import annotations

HEADER = 0xFF
FOOTER = 0xAA

CMD_MODE = 0xA1
CMD_BRIGHTNESS = 0xA2
CMD_COLOR_TEMP = 0xA3

MIN_KELVIN = 2700
MAX_KELVIN = 6500

MIN_LEVEL = 0
MAX_LEVEL = 100

# Mode values sent with CMD_MODE.
MODE_ON = 0x00
MODE_OFF_PREPARE = 0x30
MODE_OFF = 0x01

EFFECTS: dict[str, int] = {
    "flash": 0x04,
    "tv": 0x05,
    "candle": 0x06,
    "strobe1": 0x0C,
    "strobe2": 0x0D,
    "strobe3": 0x0E,
}

NAME_PREFIX = "ulanzi"


def _mode(value: int) -> bytes:
    return bytes([HEADER, CMD_MODE, 0x01, value, value, FOOTER])


def power_on() -> bytes:
    """Turn the light on (also leaves any running effect)."""
    return _mode(MODE_ON)


def power_off() -> list[bytes]:
    """Turn the light off. Both packets must be sent, in this order."""
    return [_mode(MODE_OFF_PREPARE), _mode(MODE_OFF)]


def brightness(level: int) -> bytes:
    """Set brightness, ``level`` is 0-100 percent."""
    if not MIN_LEVEL <= level <= MAX_LEVEL:
        raise ValueError(f"brightness must be {MIN_LEVEL}-{MAX_LEVEL}, got {level}")
    return bytes([HEADER, CMD_BRIGHTNESS, 0x01, level, level, FOOTER])


def color_temp(kelvin: int) -> bytes:
    """Set colour temperature in Kelvin (2700-6500)."""
    if not MIN_KELVIN <= kelvin <= MAX_KELVIN:
        raise ValueError(f"kelvin must be {MIN_KELVIN}-{MAX_KELVIN}, got {kelvin}")
    hi, lo = divmod(kelvin, 256)
    checksum = (hi + lo) % 256
    return bytes([HEADER, CMD_COLOR_TEMP, 0x02, hi, lo, checksum, FOOTER])


def effect(name: str) -> bytes:
    """Start one of the built-in effects listed in ``EFFECTS``."""
    try:
        value = EFFECTS[name]
    except KeyError:
        raise ValueError(f"unknown effect {name!r}") from None
    return _mode(value)


def clamp_kelvin(kelvin: float) -> int:
    """Round and clamp a Kelvin value into the supported range."""
    return max(MIN_KELVIN, min(MAX_KELVIN, round(kelvin)))


def ha_brightness_to_level(value: float) -> int:
    """Map Home Assistant brightness (0-255) to device level 1-100.

    Never returns 0: level 0 while on is pointless, and "off" has its own command.
    """
    return max(1, min(MAX_LEVEL, round(value * MAX_LEVEL / 255)))


def is_ulanzi_name(name: str | None) -> bool:
    """Return True if a BLE advertised name looks like an Ulanzi light."""
    return bool(name) and name.strip().lower().startswith(NAME_PREFIX)
