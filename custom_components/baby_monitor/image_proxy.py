"""Signed same-origin image proxy for crib item crops."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import re
from urllib.parse import quote

from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import DOMAIN

ITEM_IMAGE_PATH = "/api/baby_monitor/{entry_id}/item-image/{item_id}"
ATTENTION_IMAGE_PATH = "/api/baby_monitor/{entry_id}/attention-image"
_ITEM_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def item_image_sig(entry_id: str, item_id: str, token: str) -> str:
    payload = f"{entry_id}:{item_id}".encode()
    return hmac.new(token.encode(), payload, hashlib.sha256).hexdigest()[:32]


def item_image_url(entry_id: str, item_id: str, token: str) -> str:
    safe_id = quote(item_id, safe="")
    path = ITEM_IMAGE_PATH.format(entry_id=quote(entry_id, safe=""), item_id=safe_id)
    return f"{path}?sig={item_image_sig(entry_id, item_id, token)}"


def attention_image_sig(entry_id: str, token: str) -> str:
    payload = f"{entry_id}:attention-image".encode()
    return hmac.new(token.encode(), payload, hashlib.sha256).hexdigest()[:32]


def attention_image_url(entry_id: str, token: str) -> str:
    path = ATTENTION_IMAGE_PATH.format(entry_id=quote(entry_id, safe=""))
    return f"{path}?sig={attention_image_sig(entry_id, token)}"


def valid_item_id(item_id: str) -> bool:
    return bool(_ITEM_ID_RE.fullmatch(item_id))


async def async_register_item_image_view(hass) -> None:
    if hass.data.get(f"{DOMAIN}_item_image_view"):
        return

    from aiohttp import web
    from homeassistant.components.http import HomeAssistantView

    class BabyMonitorItemImageView(HomeAssistantView):
        url = "/api/baby_monitor/{entry_id}/item-image/{item_id}"
        name = "api:baby_monitor:item_image"
        requires_auth = False

        async def get(self, request, entry_id: str, item_id: str):
            sig = request.query.get("sig", "")
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry is None or entry.domain != DOMAIN or not valid_item_id(item_id):
                raise web.HTTPNotFound()

            token = entry.data.get("token", "")
            if not hmac.compare_digest(sig, item_image_sig(entry.entry_id, item_id, token)):
                raise web.HTTPUnauthorized()

            session = async_create_clientsession(hass, verify_ssl=False)
            host = entry.data["host"].rstrip("/")
            try:
                async with asyncio.timeout(10):
                    resp = await session.get(
                        f"{host}/api/item-image/{item_id}",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    body = await resp.read()
            except Exception as err:
                raise web.HTTPBadGateway() from err

            if resp.status == 404:
                raise web.HTTPNotFound()
            if resp.status in (401, 403):
                raise web.HTTPBadGateway()
            try:
                resp.raise_for_status()
            except Exception as err:
                raise web.HTTPBadGateway() from err

            return web.Response(
                body=body,
                headers={
                    "Cache-Control": "private, max-age=30",
                    "Content-Type": resp.headers.get("Content-Type", "image/jpeg"),
                },
            )

    class BabyMonitorAttentionImageView(HomeAssistantView):
        url = "/api/baby_monitor/{entry_id}/attention-image"
        name = "api:baby_monitor:attention_image"
        requires_auth = False

        async def get(self, request, entry_id: str):
            sig = request.query.get("sig", "")
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry is None or entry.domain != DOMAIN:
                raise web.HTTPNotFound()

            token = entry.data.get("token", "")
            if not hmac.compare_digest(sig, attention_image_sig(entry.entry_id, token)):
                raise web.HTTPUnauthorized()

            session = async_create_clientsession(hass, verify_ssl=False)
            host = entry.data["host"].rstrip("/")
            try:
                async with asyncio.timeout(10):
                    resp = await session.get(
                        f"{host}/api/attention-image",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    body = await resp.read()
            except Exception as err:
                raise web.HTTPBadGateway() from err

            if resp.status == 404:
                raise web.HTTPNotFound()
            if resp.status in (401, 403):
                raise web.HTTPBadGateway()
            try:
                resp.raise_for_status()
            except Exception as err:
                raise web.HTTPBadGateway() from err

            return web.Response(
                body=body,
                headers={
                    "Cache-Control": "private, max-age=30",
                    "Content-Type": resp.headers.get("Content-Type", "image/jpeg"),
                },
            )

    hass.http.register_view(BabyMonitorItemImageView())
    hass.http.register_view(BabyMonitorAttentionImageView())
    hass.data[f"{DOMAIN}_item_image_view"] = True
