"""Fork-only Room Assist options, kept out of scheduler.py to ease upstream rebases.

All options are off by default; defaults reproduce upstream behaviour exactly.
Only fixed heat/cool scalar targets are affected (not auto, not range targets).
"""

from __future__ import annotations

import math
from typing import Any, Literal

FORK_OPTION_DEFAULTS: dict[str, Any] = {
    "room_sensor_assist_demand_gain": 1.0,
    "room_sensor_assist_directional_limit": False,
    "room_sensor_assist_demand_fan_mode": None,
    "room_sensor_assist_demand_fan_delta": 1.5,
    "room_sensor_assist_quiet_start": None,
    "room_sensor_assist_quiet_end": None,
    "single_command_delivery": False,
}


def in_quiet_period(config: Any, now: Any) -> bool:
    """Return whether Room Assist is silenced at this local time.

    Between `quiet_start` and `quiet_end` ("HH:MM", may span midnight) Room
    Assist is treated as disabled: the scheduled target is restored once and
    then left alone, so the device receives no further commands.
    """
    start = config.get("room_sensor_assist_quiet_start")
    end = config.get("room_sensor_assist_quiet_end")
    if not start or not end or start == end:
        return False
    current = now.strftime("%H:%M")
    return start <= current < end if start < end else current >= start or current < end


def without_fork_options(config: Any) -> Any:
    """Return a config copy on which the fork options are inactive."""
    return {**config, **FORK_OPTION_DEFAULTS}


def demand_gain_error(
    config: Any, direction: str, fixed_direction: bool, error: float
) -> float:
    """Amplify the room error only while the room still requests this direction.

    Upstream applies the raw error as offset, which merely cancels the sensor
    bias. A gain > 1 asks the device for more while the room is far from the
    target and fades to nothing as the room reaches it (no integral, no state).
    """
    gain = config.get("room_sensor_assist_demand_gain", 1.0)
    demanding = (direction == "heat" and error > 0) or (direction == "cool" and error < 0)
    return error * gain if fixed_direction and demanding else error


def demand_fan_mode(
    config: Any,
    direction: str,
    fixed_direction: bool,
    error: float,
    previous: str | None,
) -> str | None:
    """Return the catch-up fan mode while the room is far from its target.

    `error` is scheduled target minus room temperature. The fan mode engages at
    `demand_fan_delta` and is released at half of it, so it does not flap; None
    means the scheduled block's own fan mode applies.
    """
    fan_mode = config.get("room_sensor_assist_demand_fan_mode")
    if not fan_mode or not fixed_direction:
        return None
    delta = config.get("room_sensor_assist_demand_fan_delta", 1.5)
    demand = error if direction == "heat" else -error if direction == "cool" else 0.0
    if demand >= delta or (previous == fan_mode and demand > delta / 2):
        return fan_mode
    return None


def apply_directional_limit(
    config: Any,
    direction: str,
    fixed_direction: bool,
    desired: float,
    target: float,
    step: float | None,
    minimum: float,
) -> tuple[float, Literal["heating_floor", "cooling_ceiling"] | None]:
    """Keep the delivered setpoint on the demand side of the scheduled target.

    Heat: never below the target; cool: never above. The bound is the first
    representable step on the demand side, so the later direction-aware
    stepping cannot cross it. Device limits are applied afterwards by the
    caller and still win.
    """
    if not fixed_direction or not config.get("room_sensor_assist_directional_limit"):
        return desired, None
    stepped = isinstance(step, int | float) and math.isfinite(step) and step > 0
    units = (target - minimum) / step if stepped else 0.0
    if direction == "heat":
        bound = minimum + math.ceil(units - 0.000001) * step if stepped else target
        if desired < bound - 0.000001:
            return bound, "heating_floor"
    elif direction == "cool":
        bound = minimum + math.floor(units + 0.000001) * step if stepped else target
        if desired > bound + 0.000001:
            return bound, "cooling_ceiling"
    return desired, None
