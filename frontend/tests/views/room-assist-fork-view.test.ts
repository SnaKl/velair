// @vitest-environment jsdom
import { render } from "lit";
import { describe, expect, it, vi } from "vitest";
import { preconditioningSettings } from "../../src/velair/domain/preconditioning";
import { renderRoomAssistForkSettings } from "../../src/velair/views/room-assist-fork-view";

function mount(value: Record<string, unknown>) {
  const save = vi.fn();
  const host = {
    _language: () => "fr",
    _settingsSaving: false,
    _saveZonePreconditioning: save,
    hass: { states: { "climate.salon": { attributes: { fan_modes: ["auto", "high"] } } } },
  };
  const settings = preconditioningSettings({
    room_temperature_entity_id: "sensor.salon",
    room_sensor_assist_enabled: true,
    ...value,
  });
  const container = document.createElement("div");
  render(renderRoomAssistForkSettings(host as never, "climate.salon", settings, "°C"), container);
  const field = <T extends HTMLElement>(name: string) =>
    container.querySelector<T>(`#room-assist-fork-climate-salon-room_sensor_assist_${name}`)!;
  return { container, field, save };
}

describe("room assist fork settings", () => {
  it("shows upstream defaults when no fork option is stored", () => {
    const { field, container } = mount({});
    expect(field<HTMLInputElement>("demand_gain").value).toBe("1");
    expect(field<HTMLInputElement>("directional_limit").checked).toBe(false);
    expect(field<HTMLSelectElement>("demand_fan_mode").value).toBe("");
    expect(field<HTMLInputElement>("demand_fan_delta").value).toBe("1.5");
    expect(container.textContent).toContain("Options du fork");
  });

  it("shows stored values and saves each change", () => {
    const { field, save } = mount({
      room_sensor_assist_demand_gain: 2,
      room_sensor_assist_directional_limit: true,
      room_sensor_assist_demand_fan_mode: "high",
    });
    expect(field<HTMLInputElement>("demand_gain").value).toBe("2");
    expect(field<HTMLInputElement>("directional_limit").checked).toBe(true);
    expect(field<HTMLSelectElement>("demand_fan_mode").value).toBe("high");

    const gain = field<HTMLInputElement>("demand_gain");
    gain.value = "9";
    gain.dispatchEvent(new Event("change"));
    expect(save).toHaveBeenLastCalledWith("climate.salon", { room_sensor_assist_demand_gain: 3 });

    const limit = field<HTMLInputElement>("directional_limit");
    limit.checked = false;
    limit.dispatchEvent(new Event("change"));
    expect(save).toHaveBeenLastCalledWith("climate.salon", { room_sensor_assist_directional_limit: false });

    const fan = field<HTMLSelectElement>("demand_fan_mode");
    fan.value = "";
    fan.dispatchEvent(new Event("change"));
    expect(save).toHaveBeenLastCalledWith("climate.salon", { room_sensor_assist_demand_fan_mode: null });
  });

  it("is disabled while Room Assist is off", () => {
    const { field } = mount({ room_sensor_assist_enabled: false });
    expect(field<HTMLInputElement>("demand_gain").disabled).toBe(true);
    expect(field<HTMLSelectElement>("demand_fan_mode").disabled).toBe(true);
  });
});
