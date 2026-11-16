"""Fork-only quiet delivery: drop unchanged commands, one Sensibo call for the rest."""

from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from . import helpers  # noqa: F401 - installs Home Assistant test stubs
from custom_components.velair import delivery_fork
from custom_components.velair.climate_manager import ClimateManager


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    async def async_call(self, domain, service, data, *, blocking=False, context=None):
        self.calls.append((domain, service, dict(data)))


class SingleCommandDeliveryTest(unittest.IsolatedAsyncioTestCase):
    def _manager(self, *, enabled: bool = True, platform: str | None = None) -> ClimateManager:
        state = SimpleNamespace(
            state="heat",
            attributes={
                "temperature": 20.0, "fan_mode": "auto", "target_temp_step": 1,
                "min_temp": 16, "max_temp": 29, "supported_features": 9,
                "hvac_modes": ["off", "heat", "cool"], "fan_modes": ["auto", "high"],
            },
        )
        hass = SimpleNamespace(
            services=_Recorder(),
            states={"climate.room": state},
            config=SimpleNamespace(units=SimpleNamespace(temperature_unit="°C")),
        )
        manager = ClimateManager(hass)
        if enabled:
            manager.single_command_delivery = lambda _entity: True
        patcher = patch.object(delivery_fork, "_platform", return_value=platform)
        patcher.start()
        self.addCleanup(patcher.stop)
        return manager

    def _services(self, manager: ClimateManager) -> list[str]:
        return [f"{domain}.{service}" for domain, service, _ in manager._hass.services.calls]

    async def test_upstream_sends_every_command_when_the_option_is_off(self) -> None:
        manager = self._manager(enabled=False)
        await manager.async_set_temperature("climate.room", 21, hvac_mode="heat", fan_mode="auto")
        self.assertEqual(
            self._services(manager),
            ["climate.set_hvac_mode", "climate.set_fan_mode", "climate.set_temperature"],
        )

    async def test_unchanged_mode_and_fan_are_not_resent(self) -> None:
        manager = self._manager()
        await manager.async_set_temperature("climate.room", 21, hvac_mode="heat", fan_mode="auto")
        self.assertEqual(self._services(manager), ["climate.set_temperature"])
        self.assertEqual(manager._expected["climate.room"][0]["expected"], {"temperature": 21.0})

    async def test_changed_fan_is_still_sent_on_a_generic_device(self) -> None:
        manager = self._manager()
        await manager.async_set_temperature("climate.room", 23, hvac_mode="heat", fan_mode="high")
        self.assertEqual(self._services(manager), ["climate.set_fan_mode", "climate.set_temperature"])

    async def test_sensibo_gets_one_call_for_fan_and_temperature(self) -> None:
        manager = self._manager(platform="sensibo")
        await manager.async_set_temperature("climate.room", 23, hvac_mode="heat", fan_mode="high")
        self.assertEqual(
            manager._hass.services.calls,
            [("sensibo", "full_state", {
                "entity_id": "climate.room", "mode": "heat",
                "target_temperature": 23, "fan_mode": "high",
            })],
        )
        self.assertEqual(manager._expected["climate.room"][0]["expected"], {"temperature": 23.0})

    async def test_sensibo_mode_change_and_plain_setpoint(self) -> None:
        manager = self._manager(platform="sensibo")
        await manager.async_set_temperature("climate.room", 24, hvac_mode="cool", fan_mode="auto")
        self.assertEqual(
            manager._hass.services.calls,
            [("sensibo", "full_state", {"entity_id": "climate.room", "mode": "cool", "target_temperature": 24})],
        )
        manager._hass.services.calls.clear()
        await manager.async_set_temperature("climate.room", 22, hvac_mode="heat", fan_mode="auto")
        self.assertEqual(self._services(manager), ["climate.set_temperature"])

    async def test_sensibo_falls_back_for_modes_it_names_differently(self) -> None:
        manager = self._manager(platform="sensibo")
        manager._hass.states["climate.room"].attributes["hvac_modes"].append("fan_only")
        manager._hass.states["climate.room"].state = "fan_only"
        await manager.async_set_temperature("climate.room", 22, fan_mode="high", temperature_only=False)
        self.assertEqual(self._services(manager), ["climate.set_fan_mode", "climate.set_temperature"])


if __name__ == "__main__":
    unittest.main()
