"""Live camera entity backed by the go2rtc RTSP restream (real video, not snapshots)."""

from __future__ import annotations

from urllib.parse import urlparse

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.components.ffmpeg import async_get_image

from .const import DOMAIN


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
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(self, entry) -> None:
        super().__init__()
        self._stream = _stream_url(entry)
        self._attr_unique_id = f"{entry.entry_id}_camera"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Baby Monitor",
            "manufacturer": "baby-status-monitor",
        }

    async def stream_source(self) -> str:
        return self._stream

    async def async_camera_image(self, width=None, height=None):
        # A frame grabbed by ffmpeg for the card preview; the live stream plays on click.
        return await async_get_image(self.hass, self._stream, width=width, height=height)
