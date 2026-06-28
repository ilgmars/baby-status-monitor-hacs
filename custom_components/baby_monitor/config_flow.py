"""Config flow: ask for the dashboard URL and the API token, then verify them."""

from __future__ import annotations

import asyncio

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import DOMAIN


class BabyMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input["host"].rstrip("/")
            session = async_create_clientsession(self.hass, verify_ssl=False)
            try:
                async with asyncio.timeout(10):
                    resp = await session.get(
                        f"{host}/api/status",
                        headers={"Authorization": f"Bearer {user_input['token']}"},
                    )
                if resp.status == 401:
                    errors["base"] = "invalid_auth"
                elif resp.status != 200:
                    errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - any failure means we can't reach it
                errors["base"] = "cannot_connect"
            if not errors:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Baby Monitor",
                    data={
                        "host": host,
                        "token": user_input["token"],
                        "stream_url": user_input.get("stream_url", "").strip(),
                    },
                )

        schema = vol.Schema(
            {
                vol.Required("host", default="https://192.168.1.10"): str,
                vol.Required("token"): str,
                # Blank = use the go2rtc restream on the dashboard host (rtsp://<host>:8554/cam).
                vol.Optional("stream_url", default=""): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
