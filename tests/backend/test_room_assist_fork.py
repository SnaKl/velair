"""Fork-only Room Assist options: demand gain and directional setpoint limit."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from .helpers import normalize_preconditioning_data
from . import test_scheduler_application as upstream


def _config(**options):
    return normalize_preconditioning_data(
        {"room_sensor_assist_deadband": 0.7, "room_sensor_assist_max_delta": 5, **options}
    )


class RoomAssistForkTest(upstream.VelairSchedulerPreconditioningTest):
    def setUp(self) -> None:
        super().setUp()
        self.climate.steps[self.entity_id] = 1
        self.climate.limits[self.entity_id] = (16, 29)

    def _target(self, config, direction, target, room, climate, **kwargs):
        return self.scheduler._room_sensor_assist_target(
            self.entity_id, config, direction, target, room, climate, **kwargs
        )

    def test_defaults_are_not_stored_and_reproduce_upstream(self) -> None:
        config = _config()
        self.assertNotIn("room_sensor_assist_demand_gain", config)
        self.assertNotIn("room_sensor_assist_directional_limit", config)
        # Observed on 2026-11-15: target 20 (towards_upper 20.7), room 17.3, PAC 18.4 -> 21.
        result = self._target(
            config, "heat", 20, 17.3, 18.4,
            hysteresis_phase="towards_upper", hysteresis_target=20.7,
        )
        self.assertEqual(result.applied_temperature, 21)
        # Observed on 2026-11-13: room above target, setpoint dropped to 19.
        below = self._target(
            config, "heat", 20, 20.3, 20.9,
            hysteresis_phase="towards_lower", hysteresis_target=19.3,
        )
        self.assertEqual(below.applied_temperature, 19)
        self.assertIsNone(below.directional_limit)

    def test_option_normalization(self) -> None:
        self.assertEqual(_config(room_sensor_assist_demand_gain=2)["room_sensor_assist_demand_gain"], 2.0)
        self.assertEqual(_config(room_sensor_assist_demand_gain=9)["room_sensor_assist_demand_gain"], 3.0)
        self.assertNotIn("room_sensor_assist_demand_gain", _config(room_sensor_assist_demand_gain="x"))
        self.assertTrue(_config(room_sensor_assist_directional_limit=True)["room_sensor_assist_directional_limit"])

    def test_gain_raises_demand_only_while_room_requests_it(self) -> None:
        config = _config(room_sensor_assist_demand_gain=2)
        far = self._target(
            config, "heat", 20, 17.3, 18.4,
            hysteresis_phase="towards_upper", hysteresis_target=20.7,
        )
        self.assertEqual(far.applied_temperature, 23)  # 18.4 + min(5, 2 * 3.4), floored
        near = self._target(
            config, "heat", 20, 20.5, 21.5,
            hysteresis_phase="towards_upper", hysteresis_target=20.7,
        )
        self.assertEqual(near.applied_temperature, 21)  # 21.5 + 0.4, gain fades out
        braking = self._target(
            config, "heat", 20, 20.8, 21.8,
            hysteresis_phase="towards_lower", hysteresis_target=19.3,
        )
        self.assertEqual(braking.applied_temperature, 20)  # 21.8 - 1.5: not amplified
        cooling = self._target(
            config, "cool", 24, 26, 25,
            hysteresis_phase="towards_lower", hysteresis_target=23.3,
        )
        self.assertEqual(cooling.applied_temperature, 20)  # 25 - min(5, 2 * 2.7), ceiled

    def test_gain_respects_max_delta_device_limits_and_auto(self) -> None:
        config = _config(room_sensor_assist_demand_gain=3)
        limited = self._target(config, "heat", 22, 16, 27)
        self.assertEqual(limited.applied_temperature, 29)
        self.assertEqual(limited.limited_by, "maximum")
        auto = self._target(config, "heat", 20, 18, 19, fixed_direction=False)
        self.assertEqual(auto.applied_temperature, 21)  # upstream: 19 + 2

    def test_directional_limit_heating_floor(self) -> None:
        config = _config(room_sensor_assist_directional_limit=True)
        held = self._target(
            config, "heat", 20, 20.3, 20.9,
            hysteresis_phase="towards_lower", hysteresis_target=19.3,
        )
        self.assertEqual(held.applied_temperature, 20)
        self.assertEqual(held.directional_limit, "heating_floor")
        self.assertIsNone(held.scheduled_target_guard)
        raised = self._target(
            config, "heat", 20, 17.3, 18.4,
            hysteresis_phase="towards_upper", hysteresis_target=20.7,
        )
        self.assertEqual(raised.applied_temperature, 21)
        self.assertIsNone(raised.directional_limit)
        reduced = self._target(  # the floor follows the active target, not 20
            config, "heat", 17, 19, 20,
            hysteresis_phase="towards_lower", hysteresis_target=16.3,
        )
        self.assertEqual(reduced.applied_temperature, 17)

    def test_directional_limit_cooling_ceiling(self) -> None:
        config = _config(room_sensor_assist_directional_limit=True)
        held = self._target(
            config, "cool", 26, 25.5, 25,
            hysteresis_phase="towards_upper", hysteresis_target=26.7,
        )
        self.assertEqual(held.applied_temperature, 26)
        self.assertEqual(held.directional_limit, "cooling_ceiling")
        lowered = self._target(
            config, "cool", 26, 28, 27,
            hysteresis_phase="towards_lower", hysteresis_target=25.3,
        )
        self.assertEqual(lowered.applied_temperature, 25)
        self.assertIsNone(lowered.directional_limit)

    def test_directional_limit_fractional_target_and_device_limits(self) -> None:
        config = _config(room_sensor_assist_directional_limit=True)
        heat = self._target(
            config, "heat", 20.5, 21.5, 22,
            hysteresis_phase="towards_lower", hysteresis_target=19.8,
        )
        self.assertEqual(heat.applied_temperature, 21)  # first step at or above 20.5
        cool = self._target(
            config, "cool", 25.5, 24, 23,
            hysteresis_phase="towards_upper", hysteresis_target=26.2,
        )
        self.assertEqual(cool.applied_temperature, 25)  # first step at or below 25.5
        self.climate.limits[self.entity_id] = (16, 19)
        conflict = self._target(
            config, "heat", 20, 20.3, 20.9,
            hysteresis_phase="towards_lower", hysteresis_target=19.3,
        )
        self.assertEqual(conflict.applied_temperature, 19)  # device limit wins
        self.assertEqual(conflict.limited_by, "maximum")

    def test_directional_limit_holds_with_gain_and_skips_auto(self) -> None:
        config = _config(
            room_sensor_assist_directional_limit=True, room_sensor_assist_demand_gain=3
        )
        for room in (16.0, 18.0, 19.5, 20.0, 20.6, 21.0, 23.0):
            for phase, phase_target in (("towards_upper", 20.7), ("towards_lower", 19.3)):
                with self.subTest(room=room, phase=phase):
                    result = self._target(
                        config, "heat", 20, room, room + 1,
                        hysteresis_phase=phase, hysteresis_target=phase_target,
                    )
                    self.assertGreaterEqual(result.applied_temperature, 20)
                    self.assertLessEqual(result.applied_temperature, 29)
        auto = self._target(config, "heat", 20, 22, 23, fixed_direction=False)
        self.assertEqual(auto.applied_temperature, 21)  # upstream: 23 - 2
        self.assertIsNone(auto.directional_limit)

class RoomAssistDemandFanTest(upstream.VelairSchedulerPreconditioningTest):
    """Catch-up fan mode delivered with the Room Assist setpoint."""

    def setUp(self) -> None:
        super().setUp()
        self.climate.steps[self.entity_id] = 1
        self.climate.limits[self.entity_id] = (16, 29)
        self.climate.climate_options[self.entity_id] = {"fan_mode": ["auto", "high"]}
        self.sensor = "sensor.salon_temperature"
        self.data["zones"][self.entity_id]["preconditioning"].update(
            room_temperature_entity_id=self.sensor,
            room_sensor_assist_enabled=True,
            room_sensor_assist_deadband=0.7,
            room_sensor_assist_max_delta=5,
        )
        self.data["zones"][self.entity_id]["schedule"]["tuesday"] = [
            {"start": "17:00", "action": "set_temperature", "temperature": 20,
             "hvac_mode": "heat", "fan_mode": "auto"}
        ]

    async def _refresh(self, room: float) -> str | None:
        """Refresh Room Assist at one room temperature; return the delivered fan mode."""
        self.hass.states[self.sensor] = SimpleNamespace(
            state=str(room), attributes={"unit_of_measurement": "°C"}
        )
        self.hass.states[self.entity_id] = SimpleNamespace(
            state="heat", attributes={"current_temperature": room + 1, "temperature": 20}
        )
        self.climate.calls.clear()
        await self.refresh_assist(
            self.scheduler, self.entity_id, target_temperature=20, hvac_mode="heat",
            weekday="tuesday", start="17:00", reason="current_schedule",
        )
        if not self.climate.calls:
            return None
        call = self.climate.calls[-1]
        return call[5]["fan_mode"] if len(call) > 5 else "none"

    async def test_block_fan_mode_is_kept_without_the_option(self) -> None:
        self.assertEqual(await self._refresh(17.0), "auto")

    async def test_catch_up_fan_engages_far_and_releases_near_target(self) -> None:
        self.data["zones"][self.entity_id]["preconditioning"][
            "room_sensor_assist_demand_fan_mode"
        ] = "high"
        self.assertEqual(await self._refresh(17.0), "high")  # 3.0 behind
        status = self.read_scheduler(self.scheduler, "_room_sensor_assist_status", self.entity_id)
        self.assertEqual(status["demand_fan_mode"], "high")
        self.assertIn(await self._refresh(19.0), ("high", None))  # 1.0 behind: held
        self.assertEqual(
            self.scheduler._room_sensor_assist_states[self.entity_id].demand_fan_mode, "high"
        )
        # 0.7 behind: released, and delivered even if the setpoint did not move.
        self.assertEqual(await self._refresh(19.3), "auto")
        self.assertIsNone(
            self.scheduler._room_sensor_assist_states[self.entity_id].demand_fan_mode
        )
        self.assertIn(await self._refresh(18.9), ("auto", None))  # 1.1 behind: no re-engage

    async def test_unsupported_fan_mode_is_ignored(self) -> None:
        self.data["zones"][self.entity_id]["preconditioning"][
            "room_sensor_assist_demand_fan_mode"
        ] = "turbo"
        self.assertEqual(await self._refresh(17.0), "auto")


def load_tests(loader, tests, pattern):
    """Run only the tests defined here, not the inherited upstream suite."""
    return unittest.TestSuite(
        case(name)
        for case in (RoomAssistForkTest, RoomAssistDemandFanTest)
        for name in vars(case)
        if name.startswith("test_")
    )


if __name__ == "__main__":
    unittest.main()
