"""Whether a scan is running (admins)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BeateraConfigEntry
from .entity import BeateraServerEntity


async def async_setup_entry(hass: HomeAssistant, entry: BeateraConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    if entry.runtime_data.admin:
        add([Scanning(entry.runtime_data, "scanning")])


class Scanning(BeateraServerEntity, BinarySensorEntity):
    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.status.get("scanning"))

    @property
    def extra_state_attributes(self) -> dict | None:
        last = self.coordinator.data.status.get("lastScan")
        return {"last_scan": last} if last else None
