"""Numeric / text sensors: respiration rate, sleep state, cry reason."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN
from .entity import BabyEntity

# (key, name, unit)
SENSORS = [
    ("respiration_rate", "Respiration rate", "bpm"),
    ("sleep_state", "Sleep state", None),
    ("cry_reason", "Cry reason", None),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BabySensor(coordinator, entry, key, name, unit) for key, name, unit in SENSORS
    )


class BabySensor(BabyEntity, SensorEntity):
    def __init__(self, coordinator, entry, key, name, unit) -> None:
        super().__init__(coordinator, entry, key, name)
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        return self._value
