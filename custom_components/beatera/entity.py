"""What all entities of the server itself share."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BeateraCoordinator


def server_device(coordinator: BeateraCoordinator) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
        name=coordinator.config_entry.title,
        manufacturer="Beatera",
        model="Server",
        sw_version=coordinator.data.status.get("version") if coordinator.data else None,
        configuration_url=coordinator.api.base,
    )


class BeateraServerEntity(CoordinatorEntity[BeateraCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: BeateraCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}-{key}"
        self._attr_translation_key = key
        self._attr_device_info = server_device(coordinator)
