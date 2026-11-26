"""Keeps the state of the server and its players, asked regularly and told by webhooks."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BeateraApi, BeateraAuthError, BeateraError
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass
class BeateraData:
    """What the server said last."""

    status: dict[str, Any] = field(default_factory=dict)
    players: dict[str, dict[str, Any]] = field(default_factory=dict)
    modes: dict[int, dict[str, Any]] = field(default_factory=dict)


class BeateraCoordinator(DataUpdateCoordinator[BeateraData]):
    """One for each Beatera account in Home Assistant."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: BeateraApi, me: dict[str, Any]) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.api = api
        self.me = me

    @property
    def admin(self) -> bool:
        return "admin" in (self.me.get("scopes") or []) and bool(self.me.get("user", {}).get("admin"))

    async def _async_update_data(self) -> BeateraData:
        try:
            status = await self.api.status()
            players = await self.api.players()
        except BeateraAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except BeateraError as err:
            raise UpdateFailed(str(err)) from err
        try:
            modes = await self.api.modes()
        except BeateraError:
            # Older servers know no modes.
            modes = []
        return BeateraData(status=status, players={player["id"]: player for player in players}, modes={mode["id"]: mode for mode in modes})

    def mode(self, name_or_id: str | int) -> dict[str, Any] | None:
        """A mode by its number or its name, ignoring case."""
        modes = self.data.modes if self.data else {}
        if str(name_or_id).isdigit() and int(name_or_id) in modes:
            return modes[int(name_or_id)]
        wanted = str(name_or_id).strip().casefold()
        return next((mode for mode in modes.values() if mode["name"].casefold() == wanted), None)
