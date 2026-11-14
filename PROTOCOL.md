# Panel bus observations — 13 November 2026

Measured on one Ultimate 9000EEV at CN1, 9600 baud, 8N1.
Payload positions below are one-based, starting after the length byte
and excluding the final XOR checksum.

| Frame | Payload byte | Observation |
| --- | ---: | --- |
| FF → 00 | 4 | OFF changed 0x63 to 0x98. ON changed it back to 0x63. |
| FF → 00 | 8 | Setpoint followed every step from 45 to 40 °C and back. In this range, °C = raw + 5 (0x23–0x28). |
| 00 → FF and FF → 40 | Last | Bit 0x10 cleared on OFF and returned on ON, matching the sun icon with the compressor stopped. |
| FF → 40 | 5 | Tank readings of 41–45 °C matched 0xA9, 0xAB, 0xAD, 0xAF and 0xB1. Candidate conversion: °C = (raw − 87) / 2. |
| 00 → FF | 9 | One heating cycle showed 0x10 → 0x18 → 0x1C → 0x18 → 0x10. Sound and electrical load corroborated compressor operation. Bit 0x04 is a candidate for compressor running. |
| 00 → FF | 6 | Candidate for discharge temperature (CHECK 07). During cooldown, several observations fit °C = raw + 3, with timing uncertainty. Validate again while heating. |

With the original panel unplugged, FF → 00 disappeared while 00 → FF,
40 → FF, 80 → FF and FF → 40 continued. FF → 00 returned after reconnection.
This strongly suggests FF → 00 originates from the panel. The captures
do not yet establish the startup exchange or whether a replacement's
messages will be accepted.

## Replacement test

Bench-test the ESP32-S2 with a Waveshare WS-27479 and the USB–RS-485
adapter at 9600 8N1. For the first pump test, disconnect the original
panel with power off, connect the ESP32/WS-27479 in its place, and leave
the USB adapter in parallel as a passive monitor with its termination
disabled. Check the original panel's termination before deciding whether
to enable the WS-27479's 120 Ω termination.

Use 3.3 V UART on the ESP side and keep its ground separate from the
isolated bus ground. The pump's +12 V stays disconnected from the
USB-powered ESP assembly. Verify stable communication and the pump's
reported ON/OFF state before testing a changed setpoint.

## Follow-up tests

The ESP replacement passed ON/OFF and setpoint tests with the original
panel disconnected. The pump completed a full heating cycle. The
published ESPHome configuration uses a 2 ms response delay.

With the pump disconnected, the ESP and passive monitor exchanged
80/80 intact test frames. After reconnecting the pump, all 38 sampled
ESP responses had the expected length and valid XOR. An intermittent
connection in the monitor branch is suspected. The cause of the
earlier malformed captures remains unconfirmed.

The Gree KFRS-9/Na-M controller manual identifies CHECK 07 as discharge
temperature, CHECK 05 as defrost sensor temperature and CHECK 12 as
defrost/terminal status. The CHECK 07 byte and conversion are still
provisional. The bus fields for CHECK 05 and CHECK 12 are unidentified.

[Controller manual, page 23](https://www.manualslib.com/manual/881653/Gree-Kfrs-9-Na-M.html?page=23)
