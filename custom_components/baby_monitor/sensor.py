"""Numeric / text sensors: respiration rate, sleep state, cry reason, LLM scene."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN
from .entity import BabyEntity
from .image_proxy import attention_image_url, item_image_url

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
    ("scene_attention_event", "Attention caption [LLM]", "caption", "mdi:card-text-outline"),
    ("scene_attention_image", "Attention image [LLM]", "available", "mdi:image-search"),
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
        self._api_host = entry.data.get("host", "").rstrip("/")
        self._api_token = entry.data.get("token", "")
        self._entry_id = entry.entry_id

    @property
    def _scene(self) -> dict:
        value = (self.coordinator.data or {}).get(self._topic_key)
        return value if isinstance(value, dict) else {}

    def _attention_reason(self) -> str:
        data = self.coordinator.data or {}
        if data.get("scene_attention") is not True:
            return ""
        event = data.get("scene_attention_event")
        if not isinstance(event, dict):
            return ""
        reason = str(event.get("reason") or "").strip()
        if reason.lower() in {"", "none", "unknown", "unavailable"}:
            return ""
        return reason

    @staticmethod
    def _matches_attention_reason(item: dict, reason: str) -> bool:
        label = str(item.get("item") or "").lower()
        text = reason.lower()
        if not label or not text:
            return False
        if label in {"stain", "wet stain", "wet spot"} and any(
            word in text for word in ("wet", "stain", "spot")
        ):
            return True
        return label in text or label.removesuffix("s") in text

    def _visible_items(self, items: list) -> list:
        reason = self._attention_reason()
        if not reason:
            return items
        return [
            item
            for item in items
            if isinstance(item, dict)
            and (
                item.get("hazard")
                or item.get("alarm")
                or item.get("warning")
                or self._matches_attention_reason(item, reason)
            )
        ]

    @property
    def native_value(self):
        value = self._scene.get(self._field)
        # Sys LLM health shows WHICH tier answers while healthy (local gpu /
        # litellm / nvidia api / cpu fallback) and the error state otherwise.
        if self._field == "llm" and value == "ok":
            return self._scene.get("llm_source") or value
        if self._field == "caption":
            reason = self._scene.get("reason")
            if not reason or reason == "none":
                return "none"
            when = self._scene.get("time")
            return f"{when} - {reason}"[:255] if when else str(reason)[:255]
        if self._topic_key == "scene_attention_image" and self._field == "available":
            return "available" if value else "none"
        # Crib items: a list of {item, hazard} -> readable state, hazards marked.
        if self._field == "items":
            value = self._visible_items(value or [])
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
            for key in ("items", "history"):
                items = attrs.get(key)
                if not isinstance(items, list):
                    continue
                attrs[key] = [
                    {
                        **item,
                        "image_url": item_image_url(
                            self._entry_id, str(item["id"]), self._api_token
                        ),
                    }
                    if isinstance(item, dict) and item.get("id")
                    else item
                    for item in items
                ]
            attrs["_api_host"] = self._api_host
        if self._topic_key == "scene_attention_image" and attrs.get("available"):
            attrs["image_url"] = attention_image_url(self._entry_id, self._api_token)
            attrs["_api_host"] = self._api_host
        return attrs
