from __future__ import annotations

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN


async def _can_connect(hass: HomeAssistant, host: str) -> bool:
    session = async_get_clientsession(hass)
    timeout = aiohttp.ClientTimeout(total=8, connect=5)
    try:
        async with session.get(f"http://{host}/events", timeout=timeout) as response:
            return response.status == 200 and "text/event-stream" in response.headers.get("Content-Type", "")
    except (aiohttp.ClientError, TimeoutError, OSError):
        return False


class Ultimate9000ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            host = user_input["host"].strip()
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()
            if await _can_connect(self.hass, host):
                return self.async_create_entry(title="Ultimate 9000EEV", data={"host": host})
            errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("host"): str}),
            errors=errors,
        )

    async def async_step_import(self, user_input):
        host = user_input["host"].strip()
        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured()
        if not await _can_connect(self.hass, host):
            return self.async_abort(reason="cannot_connect")
        return self.async_create_entry(title="Ultimate 9000EEV", data={"host": host})
