"""Camera entity backed by the dashboard's authenticated still snapshot endpoint."""

from __future__ import annotations

import time
from urllib.parse import urlparse

from homeassistant.components.camera import Camera
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import DOMAIN

SNAPSHOT_TTL_S = 60.0


def _stream_url(entry) -> str:
    url = entry.data.get("stream_url")
    if url:
        return url
    # Default to the go2rtc restream on the same host as the dashboard. Request AAC audio:
    # HA's stream only carries AAC in HLS, so without this the camera's G.711 audio is
    # dropped and the live view is silent. go2rtc transcodes it on demand.
    host = urlparse(entry.data["host"]).hostname or "127.0.0.1"
    return f"rtsp://{host}:8554/cam?video=copy&audio=aac"


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([BabyCamera(entry)])


class BabyCamera(Camera):
    _attr_has_entity_name = True
    _attr_name = "Live"

    def __init__(self, entry) -> None:
        super().__init__()
        host = entry.data["host"].rstrip("/")
        self._stream = _stream_url(entry)
        self._snapshot_url = f"{host}/api/camera-snapshot"
        self._headers = {"Authorization": f"Bearer {entry.data['token']}"}
        self._snapshot: bytes | None = None
        self._snapshot_ts = 0.0
        self._attr_unique_id = f"{entry.entry_id}_camera"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Baby Monitor",
            "manufacturer": "baby-status-monitor",
        }

    @property
    def frame_interval(self) -> float:
        """Return the frame interval."""
        return SNAPSHOT_TTL_S

    async def stream_source(self) -> str:
        return self._stream

    async def async_camera_image(self, width=None, height=None):
        if self._snapshot and time.monotonic() - self._snapshot_ts < SNAPSHOT_TTL_S:
            return self._snapshot
        session = async_create_clientsession(self.hass, verify_ssl=False)
        async with session.get(self._snapshot_url, headers=self._headers) as resp:
            if resp.status != 200:
                return self._snapshot
            self._snapshot = await resp.read()
            self._snapshot_ts = time.monotonic()
            return self._snapshot
