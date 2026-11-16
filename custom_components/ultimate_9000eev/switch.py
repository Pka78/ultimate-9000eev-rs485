from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, KEY_REQUEST


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PumpRequestSwitch(coordinator, entry)])


class PumpRequestSwitch(CoordinatorEntity, SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Pumpun ON/OFF-pyyntö"
    _attr_icon = "mdi:heat-pump"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data['host']}_{KEY_REQUEST}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data["host"])},
            name="Ultimate 9000EEV",
            model="Ultimate 9000EEV · HTTP event interface",
        )

    @property
    def available(self):
        return self.coordinator.connected and KEY_REQUEST in self.coordinator.data

    @property
    def is_on(self):
        return bool(self.coordinator.data.get(KEY_REQUEST, {}).get("value"))

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_set_pump_request(True)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_set_pump_request(False)

    @property
    def extra_state_attributes(self):
        return {"last_event": self.coordinator.data.get(KEY_REQUEST, {}).get("received_at")}
