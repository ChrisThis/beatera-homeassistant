"""Numbers of the server: what plays, how much there is, what is being worked on."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BeateraConfigEntry
from .entity import BeateraServerEntity


async def async_setup_entry(hass: HomeAssistant, entry: BeateraConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    sensors = [BeateraSensor(coordinator, "playing"), BeateraSensor(coordinator, "files"), BeateraSensor(coordinator, "version")]
    if coordinator.admin:
        sensors += [BeateraSensor(coordinator, "streams"), BeateraSensor(coordinator, "work")]
    add(sensors)


class BeateraSensor(BeateraServerEntity, SensorEntity):
    def __init__(self, coordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._key = key
        if key != "version":
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Any:
        status = self.coordinator.data.status
        if self._key == "files":
            return sum((status.get("files") or {}).values())
        return status.get(self._key)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        if self._key == "files":
            return dict(data.status.get("files") or {})
        if self._key == "playing":
            # What plays where, for templates and automations.
            return {"players": [
                {"name": player.get("name"), "title": (player.get("item") or {}).get("title"), "type": (player.get("item") or {}).get("type")}
                for player in data.players.values() if player.get("playing")
            ]}
        return None
