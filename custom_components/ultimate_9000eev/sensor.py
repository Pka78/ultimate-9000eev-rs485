from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ENTITY_NAMES, KEY_COMPRESSOR, KEY_TANK


DESCRIPTIONS = {
    KEY_TANK: SensorEntityDescription(
        key=KEY_TANK,
        name=ENTITY_NAMES[KEY_TANK],
        icon="mdi:water-thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KEY_COMPRESSOR: SensorEntityDescription(
        key=KEY_COMPRESSOR,
        name=ENTITY_NAMES[KEY_COMPRESSOR],
        icon="mdi:heat-pump",
    ),
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([UltimateSensor(coordinator, entry, desc) for desc in DESCRIPTIONS.values()])


class UltimateSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.data['host']}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data["host"])},
            name="Ultimate 9000EEV",
            model="Ultimate 9000EEV · HTTP event interface",
        )

    @property
    def available(self):
        return self.coordinator.connected and self.entity_description.key in self.coordinator.data

    @property
    def native_value(self):
        item = self.coordinator.data.get(self.entity_description.key, {})
        value = item.get("value")
        if self.entity_description.key == KEY_TANK:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        if value is None:
            return None
        return str(value)

    @property
    def extra_state_attributes(self):
        item = self.coordinator.data.get(self.entity_description.key, {})
        return {"last_event": item.get("received_at")}
