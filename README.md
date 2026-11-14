# Ultimate 9000EEV RS-485

Passive measurements of the wired display bus on an Ultimate 9000EEV.
The Gree KFRS-9/Na-M is a related reference model. Compatibility across
board and firmware revisions is unverified. The eventual goal is an ESP32
replacement for the original panel.

| CN1 display label | Wire on the tested unit |
| --- | --- |
| GND | Orange |
| A | Black |
| B | Red |
| +12 V | Brown |

Use the board labels to confirm the wiring. Keep the panel connected and
attach the RS-485 receiver in parallel with power off. The +12 V wire
powers the panel. Keep it separate from the USB adapter.

## Capture on Linux

```sh
python3 capture.py /dev/ttyUSB0 --baud 9600 --parity N --stops 1 --seconds 10 --output captures/baseline
```

The script opens the serial port read-only. Linux may require membership
in the dialout group. The output includes raw bytes and timestamped USB
read batches. A read batch can contain partial frames or multiple frames.

## Measurements

| Observation | Status |
| --- | --- |
| 9600 baud, 8N1 | Validated with complete frames and matching checksums |
| Frame starts with 7E 7E, then source, destination, 11, and body length | Observed |
| Body length includes the final XOR byte | Observed |
| 00→FF, FF→00, 40→FF, FF→40, 80→FF | Observed without key presses |
| Setpoint encoding and acceptance | Unconfirmed |
| Which physical board sends each address | Unconfirmed |
| Startup and required periodic messages | Unconfirmed |

The examples contain selected complete XOR-valid frames, one
per line, with no host paths, timestamps or terminal annotations.
The baseline was captured without key presses. During the nominal 45→44
°C test, payload byte 6 changed from 16 to 15 hex in some frames.
During the nominal 44→43 °C test, payload byte 4 changed from 56 to 55
hex while byte 6 stayed at 15. Byte numbers are one-based. These
observations do not establish a setpoint mapping. A subsequent return
test ended in an EC communication fault and was inconclusive.

- [Gree wired panel framing reference](https://github.com/maxim-smirnov/gree-wired-proto)
- [Comparable Gree RS-485 captures](https://github.com/bekmansurov/gree-hvac-protocol/issues/8)

## ESPHome panel replacement

[The ESPHome configuration](firmware/ultimate-panel.yaml) is based on
the tested 2 ms firmware for the ESP32-S2-DevKitM-1 and Waveshare
WS-27479. See [PROTOCOL.md](PROTOCOL.md) for wiring and test results.

Copy `firmware/secrets.example.yaml` to `firmware/secrets.yaml` and
fill in the Wi-Fi and OTA settings. Generate an API encryption key
with `openssl rand -base64 32`. Validate and build with
`esphome config firmware/ultimate-panel.yaml` and
`esphome compile firmware/ultimate-panel.yaml`. The HTTP controls
are unauthenticated, so keep the device on a trusted local network.
