"""Boolean states: present, breathing, crying, movement, camera online, LLM attention."""

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
    # LLM scene narration: current "needs attention" verdict (the sensor "Attention
    # reason" keeps the last event's what+when even after this clears).
    ("scene_attention", "Attention needed", "problem"),
]

# Booleans living inside the scene JSON object. (key, name, field, device_class)
SCENE_BINARY = [
    ("scene", "Face covered", "face_covered", "problem"),
    ("scene", "Baby visible", "baby_visible", "occupancy"),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [BabyBinary(coordinator, entry, key, name, dc) for key, name, dc in BINARY]
    entities += [
        BabySceneBinary(coordinator, entry, key, name, field, dc)
        for key, name, field, dc in SCENE_BINARY
    ]
    async_add_entities(entities)


class BabyBinary(BabyEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry, key, name, device_class) -> None:
        super().__init__(coordinator, entry, key, name)
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool | None:
        value = self._value
        return None if value is None else bool(value)


class BabySceneBinary(BabyEntity, BinarySensorEntity):
    """One boolean field of a scene JSON object."""

    def __init__(self, coordinator, entry, key, name, field, device_class) -> None:
        super().__init__(coordinator, entry, f"{key}_{field}", name)
        self._topic_key = key
        self._field = field
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool | None:
        value = (self.coordinator.data or {}).get(self._topic_key)
        if not isinstance(value, dict) or self._field not in value:
            return None
        return bool(value[self._field])
