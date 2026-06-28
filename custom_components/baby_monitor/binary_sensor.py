"""Boolean states: present, breathing, crying, movement, camera online."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DOMAIN
from .entity import BabyEntity

# (key, name, device_class)
BINARY = [
    ("present", "Baby present", "occupancy"),
    ("breathing_detected", "Breathing detected", None),
    ("breathing_degraded", "Breathing detection degraded", "problem"),
    ("crying", "Crying", "sound"),
    ("movement", "Movement", "motion"),
    ("camera_online", "Camera online", "connectivity"),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(BabyBinary(coordinator, entry, key, name, dc) for key, name, dc in BINARY)


class BabyBinary(BabyEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry, key, name, device_class) -> None:
        super().__init__(coordinator, entry, key, name)
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool | None:
        value = self._value
        return None if value is None else bool(value)
