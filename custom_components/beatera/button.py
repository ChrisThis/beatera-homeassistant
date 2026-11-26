"""Starts a scan of all libraries (admins), and one button for each mode ("Beatera scene")."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BeateraConfigEntry
from .api import BeateraError
from .coordinator import BeateraCoordinator
from .entity import BeateraServerEntity


async def async_setup_entry(hass: HomeAssistant, entry: BeateraConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    if coordinator.admin:
        add([ScanButton(coordinator, "scan")])
    known: set[int] = set()

    @callback
    def appear() -> None:
        """Modes are set up in Beatera; new ones get a button without a restart."""
        new = [mode for mode in coordinator.data.modes if mode not in known]
        known.update(new)
        if new:
            add(ModeButton(coordinator, mode) for mode in new)

    appear()
    entry.async_on_unload(coordinator.async_add_listener(appear))


class ScanButton(BeateraServerEntity, ButtonEntity):
    async def async_press(self) -> None:
        try:
            await self.coordinator.api.start_scan()
        except BeateraError as err:
            raise HomeAssistantError(f"Beatera: {err}") from err
        await self.coordinator.async_request_refresh()


class ModeButton(BeateraServerEntity, ButtonEntity):
    """Starts the mode with what is set in Beatera; the action beatera.start_mode can choose more."""

    _attr_icon = "mdi:playlist-star"

    def __init__(self, coordinator: BeateraCoordinator, mode: int) -> None:
        super().__init__(coordinator, f"mode-{mode}")
        self._mode = mode
        self._attr_translation_key = "mode"
        self._attr_translation_placeholders = {"name": coordinator.data.modes[mode]["name"]}

    @property
    def _data(self) -> dict[str, Any] | None:
        return self.coordinator.data.modes.get(self._mode)

    @property
    def available(self) -> bool:
        return super().available and self._data is not None

    async def async_press(self) -> None:
        try:
            await self.coordinator.api.start_mode(self._mode)
        except BeateraError as err:
            raise HomeAssistantError(f"Beatera: {err}") from err
        await self.coordinator.async_request_refresh()
