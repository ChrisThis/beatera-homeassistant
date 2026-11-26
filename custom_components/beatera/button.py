"""Starts a scan of all libraries (admins)."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BeateraConfigEntry
from .api import BeateraError
from .entity import BeateraServerEntity


async def async_setup_entry(hass: HomeAssistant, entry: BeateraConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    if entry.runtime_data.admin:
        add([ScanButton(entry.runtime_data, "scan")])


class ScanButton(BeateraServerEntity, ButtonEntity):
    async def async_press(self) -> None:
        try:
            await self.coordinator.api.start_scan()
        except BeateraError as err:
            raise HomeAssistantError(f"Beatera: {err}") from err
        await self.coordinator.async_request_refresh()
