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
from .image_proxy import async_register_item_image_view

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.CAMERA]
PANEL_URL = "/baby-monitor-frontend/crib-items-panel.js"
PANEL_PATH = "crib-items"
PANEL_VERSION = "0.9.19"


async def _async_register_panel(hass: HomeAssistant) -> None:
    """Sidebar 'Crib items' panel: a CCTV wall of the objects seen in the crib.

    The integration serves its own JS (no manual /local resource setup) and
    registers a custom panel; idempotent across reloads / multiple entries.
    """
    from pathlib import Path

    from homeassistant.components import panel_custom

    if PANEL_PATH in hass.data.get("frontend_panels", {}):
        return
    js = Path(__file__).parent / "frontend" / "crib-items-panel.js"
    try:  # HA 2024.6+: async static path registration
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(PANEL_URL, str(js), cache_headers=False)]
        )
    except Exception:  # older cores: the sync API
        hass.http.register_static_path(PANEL_URL, str(js), cache_headers=False)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_PATH,
        webcomponent_name="crib-items-panel",
        sidebar_title="Crib items",
        sidebar_icon="mdi:cctv",
        module_url=f"{PANEL_URL}?v={PANEL_VERSION}",
        embed_iframe=False,
        require_admin=False,
    )


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
    await async_register_item_image_view(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    try:
        await _async_register_panel(hass)
    except Exception as err:  # the panel is cosmetic - never block sensors on it
        _LOGGER.warning("Crib items sidebar panel not registered: %s", err)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:  # last entry gone -> remove the sidebar panel
            from homeassistant.components import frontend

            frontend.async_remove_panel(hass, PANEL_PATH)
    return unloaded
