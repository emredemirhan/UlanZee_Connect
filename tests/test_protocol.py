"""Unit tests for the Ulanzi byte protocol.

protocol.py has no Home Assistant imports, so it is loaded straight from its
file (importing the package would pull in Home Assistant). Run with either:

    python3 -m unittest discover -s tests
    pytest tests
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

_PATH = Path(__file__).parents[1] / "custom_components" / "ulanzi_ble" / "protocol.py"
_spec = importlib.util.spec_from_file_location("ulanzi_protocol", _PATH)
protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protocol)


def h(text: str) -> bytes:
    return bytes.fromhex(text)


class PowerTests(unittest.TestCase):
    def test_power_on(self) -> None:
        self.assertEqual(protocol.power_on(), h("FF A1 01 00 00 AA"))

    def test_power_off_is_two_packets_in_order(self) -> None:
        self.assertEqual(
            protocol.power_off(),
            [h("FF A1 01 30 30 AA"), h("FF A1 01 01 01 AA")],
        )


class BrightnessTests(unittest.TestCase):
    def test_examples(self) -> None:
        self.assertEqual(protocol.brightness(0), h("FF A2 01 00 00 AA"))
        self.assertEqual(protocol.brightness(1), h("FF A2 01 01 01 AA"))
        self.assertEqual(protocol.brightness(50), h("FF A2 01 32 32 AA"))
        self.assertEqual(protocol.brightness(100), h("FF A2 01 64 64 AA"))

    def test_out_of_range(self) -> None:
        for level in (-1, 101, 255):
            with self.assertRaises(ValueError):
                protocol.brightness(level)

    def test_ha_brightness_mapping(self) -> None:
        self.assertEqual(protocol.ha_brightness_to_level(255), 100)
        self.assertEqual(protocol.ha_brightness_to_level(128), 50)
        self.assertEqual(protocol.ha_brightness_to_level(3), 1)
        # Never 0 while on.
        self.assertEqual(protocol.ha_brightness_to_level(1), 1)
        self.assertEqual(protocol.ha_brightness_to_level(0), 1)

    def test_every_ha_brightness_maps_to_1_100(self) -> None:
        for value in range(1, 256):
            level = protocol.ha_brightness_to_level(value)
            self.assertGreaterEqual(level, 1)
            self.assertLessEqual(level, 100)


class ColorTempTests(unittest.TestCase):
    def test_examples(self) -> None:
        # 2700 = 0x0A8C, checksum 0x0A + 0x8C = 0x96
        self.assertEqual(protocol.color_temp(2700), h("FF A3 02 0A 8C 96 AA"))
        # 4000 = 0x0FA0, checksum 0x0F + 0xA0 = 0xAF
        self.assertEqual(protocol.color_temp(4000), h("FF A3 02 0F A0 AF AA"))
        # 5600 = 0x15E0, checksum 0x15 + 0xE0 = 0xF5
        self.assertEqual(protocol.color_temp(5600), h("FF A3 02 15 E0 F5 AA"))
        # 6500 = 0x1964, checksum 0x19 + 0x64 = 0x7D
        self.assertEqual(protocol.color_temp(6500), h("FF A3 02 19 64 7D AA"))

    def test_checksum_wraps_mod_256(self) -> None:
        # 2815 = 0x0AFF, 0x0A + 0xFF = 0x109 -> 0x09
        self.assertEqual(protocol.color_temp(2815), h("FF A3 02 0A FF 09 AA"))

    def test_out_of_range(self) -> None:
        for kelvin in (2699, 6501, 0):
            with self.assertRaises(ValueError):
                protocol.color_temp(kelvin)

    def test_clamp(self) -> None:
        self.assertEqual(protocol.clamp_kelvin(2000), 2700)
        self.assertEqual(protocol.clamp_kelvin(9000), 6500)
        self.assertEqual(protocol.clamp_kelvin(4000.4), 4000)


class EffectTests(unittest.TestCase):
    def test_examples(self) -> None:
        expected = {
            "flash": "FF A1 01 04 04 AA",
            "tv": "FF A1 01 05 05 AA",
            "candle": "FF A1 01 06 06 AA",
            "strobe1": "FF A1 01 0C 0C AA",
            "strobe2": "FF A1 01 0D 0D AA",
            "strobe3": "FF A1 01 0E 0E AA",
        }
        self.assertEqual(set(protocol.EFFECTS), set(expected))
        for name, packet in expected.items():
            with self.subTest(effect=name):
                self.assertEqual(protocol.effect(name), h(packet))

    def test_unknown(self) -> None:
        with self.assertRaises(ValueError):
            protocol.effect("disco")


class NameTests(unittest.TestCase):
    def test_is_ulanzi_name(self) -> None:
        self.assertTrue(protocol.is_ulanzi_name("Ulanzi EC65"))
        self.assertTrue(protocol.is_ulanzi_name("ULANZI-1234"))
        self.assertFalse(protocol.is_ulanzi_name("ELK-BLEDOM"))
        self.assertFalse(protocol.is_ulanzi_name(""))
        self.assertFalse(protocol.is_ulanzi_name(None))


if __name__ == "__main__":
    unittest.main()
