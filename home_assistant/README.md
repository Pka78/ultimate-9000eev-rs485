# Home Assistant – Ultimate 9000EEV

The repository contains version **1.0.1** of the HA custom integration used to read and control the ESP32 panel bridge for an Ultimate 9000EEV. The live HA installation remains on its locally configured version 1.0.0; publishing this copy does not change Home Assistant. It connects to the ESP's HTTP Server-Sent Events (SSE) interface; the integration does not speak RS-485 directly and does not decode the heat-pump bus protocol.

## Install

1. Copy `custom_components/ultimate_9000eev` from the repository root into the Home Assistant configuration's `custom_components/` directory.
2. Restart Home Assistant.
3. In **Settings → Devices & services**, add **Ultimate 9000EEV** and enter the ESP's host name or IP address without a scheme or path.

The integration has no built-in host address. Set the address for the local installation. The ESP interface used here is plain HTTP and has no authentication in the tested firmware, so keep it on a trusted, segmented local network and do not expose it to the internet.

## Entities and meaning

The integration exposes four entities:

- Buffer/tank temperature (`sensor`): value reported by the ESP panel.
- Compressor status (`sensor`): the ESP's reported compressor state. It is separate from the requested pump state.
- Pump ON/OFF request (`switch`): the requested state reported by the ESP. It is not proof that the compressor has stopped or started.
- Temperature setpoint (`number`): whole degrees from 35 to 45 °C.

The event stream is required for availability. Setup waits for an initial event for each entity. Commands are sent through the ESP web controls and are accepted only after a fresh SSE snapshot reports the requested value. A planned stream refresh after a command retains the last values while reconnecting; a real connection loss makes entities unavailable and retries after a short delay.

## ESP HTTP interface used by this integration

- `GET /events`: `text/event-stream`; JSON event records identify the four values.
- `POST /switch/Pumpun ON⁄OFF-pyyntö/turn_on` and `/turn_off`: set the pump request.
- `POST /number/Lämpötilapyynti/set?value=35..45`: set the temperature request.

These routes are specific to the documented ESP panel firmware. Confirm that the firmware and route names match before adding the integration.

## Heating-source switching boundary

The integration only provides the ESP-facing temperature and pump-request controls. It does **not** control contactors or resistor stages. The live home's source-selection and phase-load automations are installation-specific and are intentionally not copied into this public package; their entity IDs, device mapping, and notification targets are not portable.

For a safe source transfer, the installation-specific controller must verify a fresh ESP acknowledgement and an actual compressor-idle report before opening the pump contactor or energizing a resistor stage. Missing, stale, or contradictory state must stop the transfer. The pump-request switch alone is not sufficient confirmation. Phase overload protection must use correctly mapped whole-house phase measurements and affect only the matching resistor stage. These interlocks need to be reviewed and commissioned for the actual wiring by a qualified installer; this integration is not a substitute for hardware protection.

## Scope and privacy

This public copy omits local network addresses, HA storage/config-entry data, user-specific dashboard YAML, home-specific scripts and automations, device identifiers, notifications, credentials, and backups. It is a manual custom integration, not a HACS release. The installed Home Assistant setup can have different local values and additional private automations.
