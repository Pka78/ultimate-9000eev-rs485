from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from urllib.parse import quote, urlencode

import aiohttp
from yarl import URL

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, ENTITIES, KEY_COMPRESSOR, KEY_REQUEST, PLATFORMS

_LOGGER = logging.getLogger(__name__)


class Ultimate9000Coordinator(DataUpdateCoordinator[dict]):
    """Consume the controller's SSE stream and issue its documented web actions."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        super().__init__(hass, _LOGGER, name="Ultimate 9000EEV", update_interval=None)
        self.host = host
        self.session = async_get_clientsession(hass)
        self.data = {}
        self.connected = False
        self._response: aiohttp.ClientResponse | None = None
        self._stream_task: asyncio.Task | None = None
        self._intentional_reconnect = False
        self._received: set[str] = set()
        self._initial = asyncio.Event()

    @property
    def events_url(self) -> str:
        return f"http://{self.host}/events"

    async def start(self) -> None:
        self._stream_task = self.hass.async_create_task(self._stream_loop())

    async def wait_initial(self, timeout: float = 15) -> None:
        await asyncio.wait_for(self._initial.wait(), timeout=timeout)

    async def stop(self) -> None:
        if self._response is not None:
            self._response.close()
        if self._stream_task is not None:
            self._stream_task.cancel()
            await asyncio.gather(self._stream_task, return_exceptions=True)

    async def _stream_loop(self) -> None:
        timeout = aiohttp.ClientTimeout(total=None, connect=8, sock_read=90)
        while True:
            try:
                async with self.session.get(self.events_url, timeout=timeout) as response:
                    self._response = response
                    if response.status != 200:
                        raise aiohttp.ClientResponseError(
                            response.request_info,
                            response.history,
                            status=response.status,
                        )
                    content_type = response.headers.get("Content-Type", "")
                    if "text/event-stream" not in content_type:
                        raise ValueError("ESP returned a non-SSE response")
                    self.connected = True
                    self.async_set_updated_data(dict(self.data))
                    async for raw_line in response.content:
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        if not line.startswith("data:"):
                            continue
                        try:
                            payload = json.loads(line[5:].strip())
                        except (json.JSONDecodeError, TypeError):
                            _LOGGER.debug("Ignoring malformed ESP event")
                            continue
                        self._handle_event(payload)
                self._response = None
            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError, ValueError) as err:
                _LOGGER.debug("Ultimate 9000EEV event stream reconnecting: %s", err)
            finally:
                self._response = None
                if self.connected and not self._intentional_reconnect:
                    self.connected = False
                    self.async_set_updated_data(dict(self.data))
            if self._intentional_reconnect:
                # Planned SSE refresh after a control action; keep entities available.
                self._intentional_reconnect = False
                await asyncio.sleep(0)
            else:
                await asyncio.sleep(3)

    def _handle_event(self, payload: dict) -> None:
        key = ENTITIES.get(payload.get("id", ""))
        if key is None:
            return
        self.data[key] = {
            "value": payload.get("value"),
            "received_at": datetime.now(timezone.utc).isoformat(),
            "received_monotonic": time.monotonic(),
            "raw_state": payload.get("state"),
        }
        self._received.add(key)
        if len(self._received) == len(ENTITIES):
            self._initial.set()
        self.async_set_updated_data(dict(self.data))

    async def _post(self, entity_id: str, action: str, query: dict | None = None) -> None:
        domain, entity_name = entity_id.split("/", 1)
        path = f"/{domain}/{quote(entity_name, safe='')}/{action}"
        if query:
            path += "?" + urlencode(query)
        url = URL(f"http://{self.host}{path}", encoded=True)
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        async with self.session.post(
            url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=timeout,
        ) as response:
            if response.status < 200 or response.status >= 300:
                raise HomeAssistantError(f"ESP command returned HTTP {response.status}")
            await response.read()

    async def _request_fresh_snapshot(self, key: str, expected, timeout: float = 15) -> None:
        # Reconnecting causes the ESP web server to send an initial state snapshot.
        before = time.monotonic()
        if self._response is not None:
            self._intentional_reconnect = True
            self._response.close()
        deadline = before + timeout
        while time.monotonic() < deadline:
            item = self.data.get(key)
            if (
                item
                and item["received_monotonic"] > before
                and expected(item["value"])
                and self.connected
            ):
                return
            await asyncio.sleep(0.1)
        raise HomeAssistantError("ESP did not confirm the requested state in a fresh event snapshot")

    async def async_set_pump_request(self, on: bool) -> None:
        if not self.connected:
            raise HomeAssistantError("ESP event stream is unavailable")
        await self._post(
            "switch/Pumpun ON⁄OFF-pyyntö",
            "turn_on" if on else "turn_off",
        )
        await self._request_fresh_snapshot(
            KEY_REQUEST,
            lambda value: value is on,
        )

    async def async_set_setpoint(self, value: float) -> None:
        if value < 35 or value > 45 or abs(value - round(value)) > 1e-6:
            raise HomeAssistantError("Setpoint must be a whole degree from 35 to 45 °C")
        if not self.connected:
            raise HomeAssistantError("ESP event stream is unavailable")
        await self._post(
            "number/Lämpötilapyynti",
            "set",
            {"value": str(int(value))},
        )
        await self._request_fresh_snapshot(
            "temperature_setpoint",
            lambda actual: str(actual) == str(int(value))
            or (isinstance(actual, (int, float)) and float(actual) == value),
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = Ultimate9000Coordinator(hass, entry.data["host"])
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.start()
    try:
        await coordinator.wait_initial()
    except (asyncio.TimeoutError, aiohttp.ClientError) as err:
        await coordinator.stop()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        raise ConfigEntryNotReady("ESP did not send all four initial states") from err
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.stop()
    return unloaded
