from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ENTITY_NAMES, KEY_SETPOINT


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TemperatureSetpoint(coordinator, entry)])


class TemperatureSetpoint(CoordinatorEntity, NumberEntity):
    _attr_has_entity_name = True
    _attr_name = ENTITY_NAMES[KEY_SETPOINT]
    _attr_icon = "mdi:thermometer-chevron-up"
    _attr_native_min_value = 35
    _attr_native_max_value = 45
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "°C"
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data['host']}_{KEY_SETPOINT}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data["host"])},
            name="Ultimate 9000EEV",
            model="Ultimate 9000EEV · HTTP event interface",
        )

    @property
    def available(self):
        return self.coordinator.connected and KEY_SETPOINT in self.coordinator.data

    @property
    def native_value(self):
        value = self.coordinator.data.get(KEY_SETPOINT, {}).get("value")
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_setpoint(value)

    @property
    def extra_state_attributes(self):
        return {"last_event": self.coordinator.data.get(KEY_SETPOINT, {}).get("received_at")}
