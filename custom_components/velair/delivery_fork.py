"""Fork-only quiet delivery: fewer device commands (and beeps) per Velair intent.

Upstream always sends set_hvac_mode, each climate option and set_temperature as
separate services, even for values the device already reports. With the per-zone
option `single_command_delivery` the unchanged ones are dropped, and a Sensibo
device gets what is left as one `sensibo.full_state` call.
"""

from __future__ import annotations

from typing import Any

SET_HVAC_MODE = "set_hvac_mode"
# Climate modes whose name is the same in sensibo.full_state.
_SENSIBO_MODES = {"heat", "cool", "dry"}


def _platform(hass: Any, entity_id: str) -> str | None:
    try:
        from homeassistant.helpers import entity_registry as er

        entry = er.async_get(hass).async_get(entity_id)
        return entry.platform if entry is not None else None
    except Exception:  # noqa: BLE001 - registry unavailable: keep generic services
        return None


def plan_single_delivery(
    hass: Any,
    entity_id: str,
    mode_service: str | None,
    mode_data: dict[str, Any],
    expected: dict[str, Any],
    target: dict[str, Any],
    climate_options: dict[str, Any],
) -> tuple[str | None, dict[str, Any], dict[str, Any] | None]:
    """Return (mode service, options, Sensibo full state) still worth sending."""
    state = hass.states.get(entity_id)
    if state is None:
        return mode_service, climate_options, None

    if mode_service == SET_HVAC_MODE and state.state == mode_data.get("hvac_mode"):
        mode_service = None
        expected.pop("hvac_mode", None)
    options = {
        key: value
        for key, value in climate_options.items()
        if value not in (None, "") and state.attributes.get(key) != value
    }

    temperature = target.get("temperature")
    mode = mode_data.get("hvac_mode") if mode_service == SET_HVAC_MODE else state.state
    if (
        (mode_service is None and not options)  # only the temperature is left
        or mode_service not in (None, SET_HVAC_MODE)
        or mode not in _SENSIBO_MODES
        or not set(options) <= {"fan_mode"}
        or not isinstance(temperature, int | float)
        or temperature != int(temperature)  # full_state takes whole degrees
        or any(value is not None for key, value in target.items() if key != "temperature")
        or _platform(hass, entity_id) != "sensibo"
    ):
        return mode_service, options, None

    full_state = {"entity_id": entity_id, "mode": mode, "target_temperature": int(temperature)}
    if "fan_mode" in options:
        full_state["fan_mode"] = options["fan_mode"]
    return mode_service, options, full_state
