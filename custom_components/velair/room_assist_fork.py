"""Fork-only Room Assist options, kept out of scheduler.py to ease upstream rebases.

Both options are off by default; defaults reproduce upstream behaviour exactly.
Only fixed heat/cool scalar targets are affected (not auto, not range targets).
"""

from __future__ import annotations

import math
from typing import Any, Literal

FORK_OPTION_DEFAULTS: dict[str, Any] = {
    "room_sensor_assist_demand_gain": 1.0,
    "room_sensor_assist_directional_limit": False,
}


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
