"""Numeric / text sensors: respiration rate, sleep state, cry reason, LLM scene."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN
from .entity import BabyEntity

# (key, name, unit)
SENSORS = [
    ("respiration_rate", "Respiration rate [ML]", "bpm"),
    ("sleep_state", "Sleep state [ML]", None),
    ("cry_reason", "Cry reason [ML]", None),
]

# LLM scene narration topics carry JSON objects; expose one field as the state and the
# whole object (incl. its time stamp) as attributes. (key, name, state_field, icon)
SCENE_SENSORS = [
    ("scene", "Latest status [LLM]", "description", "mdi:cctv"),
    ("scene", "Baby position [LLM]", "position", "mdi:human-child"),
    ("scene_attention_event", "Attention reason [LLM]", "reason", "mdi:alert-circle-outline"),
    ("scene_danger_event", "Danger reason [LLM]", "reason", "mdi:alert-octagon-outline"),
    ("scene_warning_event", "Warning reason [LLM]", "reason", "mdi:alert-outline"),
    # Objects the item scanner currently sees in the crib (list -> "pacifier, toy").
    ("scene_items", "Crib items [LLM]", "items", "mdi:cube-scan"),
    # Self-diagnostics (baby/status/health): is the monitor itself healthy.
    ("health", "Sys LLM health", "llm", "mdi:robot-outline"),
    ("health", "Sys audio health", "audio", "mdi:microphone-outline"),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [BabySensor(coordinator, entry, key, name, unit) for key, name, unit in SENSORS]
    entities += [
        BabySceneSensor(coordinator, entry, key, name, field, icon)
        for key, name, field, icon in SCENE_SENSORS
    ]
    async_add_entities(entities)


class BabySensor(BabyEntity, SensorEntity):
    def __init__(self, coordinator, entry, key, name, unit) -> None:
        super().__init__(coordinator, entry, key, name)
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        return self._value


class BabySceneSensor(BabyEntity, SensorEntity):
    """One field of a scene JSON object as state; the whole object as attributes."""

    def __init__(self, coordinator, entry, key, name, field, icon) -> None:
        # unique_id must differ per field, not just per topic key.
        super().__init__(coordinator, entry, f"{key}_{field}", name)
        self._topic_key = key
        self._field = field
        self._attr_icon = icon

    @property
    def _scene(self) -> dict:
        value = (self.coordinator.data or {}).get(self._topic_key)
        return value if isinstance(value, dict) else {}

    @property
    def native_value(self):
        value = self._scene.get(self._field)
        # Sys LLM health shows WHICH tier answers while healthy (local gpu /
        # litellm / nvidia api / cpu fallback) and the error state otherwise.
        if self._field == "llm" and value == "ok":
            return self._scene.get("llm_source") or value
        # Crib items: a list of {item, hazard} -> readable state, hazards marked.
        if self._field == "items":
            if not value:
                return "none"
            names = [
                ("\u26a0 " if it.get("hazard") else "") + str(it.get("item", "object"))
                for it in value
                if isinstance(it, dict)
            ]
            return ", ".join(names)[:255] or "none"
        return value

    @property
    def extra_state_attributes(self):
        attrs = dict(self._scene)
        if self._field == "items":
            entry_data = self.coordinator.config_entry.data
            attrs["host"] = entry_data["host"].rstrip("/")
            attrs["token"] = entry_data["token"]
        return attrs
