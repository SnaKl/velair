// Fork-only Room Assist settings. Kept in its own file, with its own labels,
// so upstream changes to sensors-view.ts and the translation files rebase cleanly.
import { html } from "lit";
import type { VelairViewHost } from "../host-types";
import type { PreconditioningSettings } from "../types";

const LABELS = {
  en: {
    title: "Fork options",
    gain: "Demand gain",
    gainHelp: "Multiplies the room-to-target gap while the room still needs heating or cooling. 1 keeps the standard behaviour.",
    limit: "Never cross the target",
    limitHelp: "Heating: the setpoint never goes below the target. Cooling: never above. Room Assist can then no longer lower the setpoint to brake an overshoot.",
    fan: "Catch-up fan mode",
    fanHelp: "Fan mode used while the room is far from the target. The scheduled fan mode returns near the target.",
    fanNone: "Off (scheduled fan mode)",
    delta: "Catch-up gap",
    deltaHelp: "Room-to-target gap that starts the catch-up fan mode. It stops at half this gap.",
    quietStart: "Quiet period start",
    quietEnd: "Quiet period end",
    quietHelp: "Between these times Room Assist leaves the scheduled setpoint alone, so the device gets no command. Clear either time to turn it off.",
    single: "Fewer commands per change",
    singleHelp: "Skips the mode and fan commands the device already has. A Sensibo device gets mode, fan and temperature as one command.",
  },
  fr: {
    title: "Options du fork",
    gain: "Gain de demande",
    gainHelp: "Multiplie l'écart pièce/cible tant que la pièce demande encore du chaud ou du froid. 1 garde le comportement standard.",
    limit: "Ne jamais franchir la cible",
    limitHelp: "Chauffage : la consigne ne descend jamais sous la cible. Froid : jamais au-dessus. Room Assist ne peut alors plus baisser la consigne pour freiner un dépassement.",
    fan: "Ventilation de rattrapage",
    fanHelp: "Mode de ventilation utilisé tant que la pièce est loin de la cible. Le mode programmé reprend à l'approche.",
    fanNone: "Désactivée (mode programmé)",
    delta: "Écart de rattrapage",
    deltaHelp: "Écart pièce/cible qui déclenche la ventilation de rattrapage. Elle s'arrête à la moitié de cet écart.",
    quietStart: "Début de la plage de silence",
    quietEnd: "Fin de la plage de silence",
    quietHelp: "Entre ces heures, Room Assist laisse la consigne programmée telle quelle : l'appareil ne reçoit aucune commande. Videz une des deux heures pour désactiver.",
    single: "Moins de commandes par changement",
    singleHelp: "N'envoie plus le mode et la ventilation que l'appareil a déjà. Un appareil Sensibo reçoit mode, ventilation et température en une seule commande.",
  },
};

function row(id: string, label: string, help: string, inactive: boolean, control: unknown, unit = "") {
  return html`
    <div class=${`sensor-config-row ${inactive ? "inactive" : ""}`}>
      <span class="label sensor-config-label"><label for=${id}>${label}</label></span>
      <span class="sensor-fork-input">${control}<span>${unit}</span></span>
      <small class="sensor-field-description" id=${`${id}-description`}>${help}</small>
    </div>
  `;
}

export function renderRoomAssistForkSettings(
  host: VelairViewHost,
  entityId: string,
  settings: PreconditioningSettings,
  unit: string,
) {
  const t = String(host._language?.() ?? "").startsWith("fr") ? LABELS.fr : LABELS.en;
  const inactive =
    !(settings.room_temperature_entity_id || settings.room_sensor_schedule?.enabled)
    || !settings.room_sensor_assist_enabled;
  const disabled = host._settingsSaving || inactive;
  const id = (field: string) => `room-assist-fork-${entityId.replace(/[^a-zA-Z0-9_-]/g, "-")}-${field}`;
  const save = (update: Record<string, unknown>) => host._saveZonePreconditioning(entityId, update);
  const number = (field: string, value: number, min: number, max: number, step: number) => html`
    <input
      id=${id(field)}
      aria-describedby=${`${id(field)}-description`}
      type="number"
      min=${String(min)}
      max=${String(max)}
      step=${String(step)}
      .value=${String(value)}
      ?disabled=${disabled}
      @change=${(event: Event) => {
        const input = event.currentTarget as HTMLInputElement;
        const raw = Number(input.value.trim());
        if (input.value.trim() === "" || !Number.isFinite(raw)) {
          input.value = String(value);
          return;
        }
        save({ [field]: Math.min(max, Math.max(min, raw)) });
      }}
    />
  `;
  const quiet = {
    room_sensor_assist_quiet_start: settings.room_sensor_assist_quiet_start ?? "",
    room_sensor_assist_quiet_end: settings.room_sensor_assist_quiet_end ?? "",
  };
  // Both times are saved together: the backend only keeps a complete period.
  const time = (field: keyof typeof quiet) => html`
    <input
      id=${id(field)}
      aria-describedby=${`${id(field)}-description`}
      type="time"
      .value=${quiet[field]}
      ?disabled=${disabled}
      @change=${(event: Event) => {
        const next = { ...quiet, [field]: (event.currentTarget as HTMLInputElement).value };
        const complete = next.room_sensor_assist_quiet_start && next.room_sensor_assist_quiet_end;
        if (complete || !next[field]) {
          save(complete ? next : { room_sensor_assist_quiet_start: null, room_sensor_assist_quiet_end: null });
        } else {
          quiet[field] = next[field];
        }
      }}
    />
  `;
  const fanMode = settings.room_sensor_assist_demand_fan_mode ?? "";
  const fanModes: string[] = host.hass?.states?.[entityId]?.attributes?.fan_modes ?? [];
  const fanOptions = fanMode && !fanModes.includes(fanMode) ? [...fanModes, fanMode] : fanModes;

  return html`
    <section class="sensor-assist-settings" aria-label=${t.title}>
      <style>
        /* Own classes: upstream tests count the inputs under .sensor-number-fields. */
        .sensor-fork-fields { display: grid; gap: 18px 24px; grid-template-columns: repeat(auto-fit, minmax(min(180px, 100%), 1fr)); align-items: start; }
        .sensor-fork-fields .sensor-config-row { border: 0; padding: 0; gap: 9px; grid-template-columns: minmax(0, 1fr); align-content: start; }
        .sensor-fork-input { align-items: center; display: grid; gap: 8px; grid-template-columns: minmax(0, 1fr) auto; }
        .sensor-fork-input > span { color: var(--secondary-text-color); font-size: 12px; white-space: nowrap; }
        .sensor-fork-input > input[type="checkbox"] { justify-self: start; height: 18px; width: 18px; }
        .sensor-config-row.inactive > .sensor-fork-input { opacity: 0.62; }
      </style>
      <h4>${t.title}</h4>
      <div class="sensor-fork-fields">
        ${row(id("room_sensor_assist_demand_gain"), t.gain, t.gainHelp, inactive,
          number("room_sensor_assist_demand_gain", settings.room_sensor_assist_demand_gain ?? 1, 1, 3, 0.1), "×")}
        ${row(id("room_sensor_assist_directional_limit"), t.limit, t.limitHelp, inactive, html`
          <input
            id=${id("room_sensor_assist_directional_limit")}
            aria-describedby=${`${id("room_sensor_assist_directional_limit")}-description`}
            type="checkbox"
            .checked=${Boolean(settings.room_sensor_assist_directional_limit)}
            ?disabled=${disabled}
            @change=${(event: Event) =>
              save({ room_sensor_assist_directional_limit: (event.currentTarget as HTMLInputElement).checked })}
          />`)}
        ${row(id("room_sensor_assist_demand_fan_mode"), t.fan, t.fanHelp, inactive, html`
          <select
            id=${id("room_sensor_assist_demand_fan_mode")}
            aria-describedby=${`${id("room_sensor_assist_demand_fan_mode")}-description`}
            ?disabled=${disabled}
            @change=${(event: Event) =>
              save({ room_sensor_assist_demand_fan_mode: (event.currentTarget as HTMLSelectElement).value || null })}
          >
            <option value="" ?selected=${!fanMode}>${t.fanNone}</option>
            ${fanOptions.map((mode) => html`<option value=${mode} ?selected=${mode === fanMode}>${mode}</option>`)}
          </select>`)}
        ${row(id("room_sensor_assist_demand_fan_delta"), t.delta, t.deltaHelp, inactive || !fanMode,
          number("room_sensor_assist_demand_fan_delta", settings.room_sensor_assist_demand_fan_delta ?? 1.5, 0.5, 5, 0.1), unit)}
        ${row(id("room_sensor_assist_quiet_start"), t.quietStart, t.quietHelp, inactive, time("room_sensor_assist_quiet_start"))}
        ${row(id("room_sensor_assist_quiet_end"), t.quietEnd, "", inactive, time("room_sensor_assist_quiet_end"))}
        ${row(id("single_command_delivery"), t.single, t.singleHelp, false, html`
          <input
            id=${id("single_command_delivery")}
            aria-describedby=${`${id("single_command_delivery")}-description`}
            type="checkbox"
            .checked=${Boolean(settings.single_command_delivery)}
            ?disabled=${host._settingsSaving}
            @change=${(event: Event) =>
              save({ single_command_delivery: (event.currentTarget as HTMLInputElement).checked })}
          />`)}
      </div>
    </section>
  `;
}
