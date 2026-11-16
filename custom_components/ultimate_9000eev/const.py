from __future__ import annotations

DOMAIN = "ultimate_9000eev"
PLATFORMS = ["sensor", "switch", "number"]

KEY_TANK = "buffer_temperature"
KEY_SETPOINT = "temperature_setpoint"
KEY_REQUEST = "power_request"
KEY_COMPRESSOR = "compressor_status"

ENTITIES = {
    "sensor/Varaajan lämpötila": KEY_TANK,
    "number/Lämpötilapyynti": KEY_SETPOINT,
    "switch/Pumpun ON⁄OFF-pyyntö": KEY_REQUEST,
    "text_sensor/Kompressorin tila": KEY_COMPRESSOR,
}

ENTITY_NAMES = {
    KEY_TANK: "Varaajan lämpötila",
    KEY_SETPOINT: "Lämpötilapyynti",
    KEY_REQUEST: "Pumpun ON/OFF-pyyntö",
    KEY_COMPRESSOR: "Kompressorin tila",
}
