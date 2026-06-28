"""Baby Status Monitor integration: polls the dashboard's /api/status over HTTP.

No MQTT needed. You give it the dashboard URL and the API_TOKEN from the server's .env.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.CAMERA]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data["host"].rstrip("/")
    token = entry.data["token"]
    # The dashboard uses a self-signed LAN cert, so don't verify TLS.
    session = async_create_clientsession(hass, verify_ssl=False)
    headers = {"Authorization": f"Bearer {token}"}

    async def _fetch() -> dict:
        try:
            async with asyncio.timeout(10):
                resp = await session.get(f"{host}/api/status", headers=headers)
                if resp.status == 401:
                    raise UpdateFailed("API token rejected")
                resp.raise_for_status()
                data = await resp.json()
        except UpdateFailed:
            raise
        except Exception as err:  # network/parse errors -> mark unavailable, keep retrying
            raise UpdateFailed(str(err)) from err
        # {"baby/status/present": {"value": true, ...}} -> {"present": true}
        return {k.removeprefix("baby/status/"): v.get("value") for k, v in data.items()}

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=_fetch,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
