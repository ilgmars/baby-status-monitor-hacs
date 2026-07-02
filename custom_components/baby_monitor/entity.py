"""Shared base entity bound to the polling coordinator."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class BabyEntity(CoordinatorEntity):
    # has_entity_name=False: buttons/tiles show the entity name alone ("Latest status
    # [LLM]"), not "Baby Monitor Latest status ..." (owner preference).
    _attr_has_entity_name = False

    def __init__(self, coordinator, entry, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Baby Monitor",
            "manufacturer": "baby-status-monitor",
        }

    @property
    def _value(self):
        return (self.coordinator.data or {}).get(self._key)
