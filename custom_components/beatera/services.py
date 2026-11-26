"""Actions of the integration: start a mode, pause everything."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_registry as er

from .api import BeateraError
from .const import DOMAIN
from .coordinator import BeateraCoordinator

START_MODE = "start_mode"
PAUSE_ALL = "pause_all"

START_SCHEMA = vol.Schema({
    vol.Required("mode"): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Optional("volume"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    vol.Optional("shuffle"): cv.boolean,
    vol.Optional("fade"): vol.All(vol.Coerce(int), vol.Range(min=0, max=60)),
    vol.Optional("when_playing"): vol.In(["replace", "append", "keep"]),
})
PAUSE_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTITY_ID): cv.entity_ids})


def _coordinators(hass: HomeAssistant) -> list[BeateraCoordinator]:
    return [entry.runtime_data for entry in hass.config_entries.async_entries(DOMAIN) if entry.state is ConfigEntryState.LOADED]


def _players(hass: HomeAssistant, entity_ids: list[str]) -> dict[str, list[str]]:
    """Beatera players by the entry they belong to; other players are not Beatera's."""
    registry = er.async_get(hass)
    found: dict[str, list[str]] = {}
    for entity_id in entity_ids:
        entity = registry.async_get(entity_id)
        if entity is None or entity.platform != DOMAIN or entity.domain != "media_player" or entity.config_entry_id is None:
            raise ServiceValidationError(f"{entity_id} is not a Beatera player")
        found.setdefault(entity.config_entry_id, []).append(entity.unique_id.removeprefix(f"{entity.config_entry_id}-"))
    return found


def async_setup_services(hass: HomeAssistant) -> None:
    async def start_mode(call: ServiceCall) -> ServiceResponse:
        players = _players(hass, call.data.get(ATTR_ENTITY_ID) or [])
        candidates = [c for c in _coordinators(hass) if not players or c.config_entry.entry_id in players]
        found = next(((c, m) for c in candidates if (m := c.mode(call.data["mode"])) is not None), None)
        if found is None:
            raise ServiceValidationError(f"Beatera knows no mode {call.data['mode']}")
        coordinator, mode = found
        volume = call.data.get("volume")
        try:
            results = await coordinator.api.start_mode(
                mode["id"], players.get(coordinator.config_entry.entry_id),
                shuffle=call.data.get("shuffle"), volume=None if volume is None else volume / 100, fade=call.data.get("fade"), busy=call.data.get("when_playing"),
                by="Home Assistant",
            )
        except BeateraError as err:
            raise HomeAssistantError(f"Beatera: {err}") from err
        await coordinator.async_request_refresh()
        return {"results": results}

    async def pause_all(call: ServiceCall) -> ServiceResponse:
        players = _players(hass, call.data.get(ATTR_ENTITY_ID) or [])
        paused: list[str] = []
        for coordinator in _coordinators(hass):
            wanted = players.get(coordinator.config_entry.entry_id)
            if players and not wanted:
                continue
            try:
                paused += await coordinator.api.pause_all(wanted)
            except BeateraError as err:
                raise HomeAssistantError(f"Beatera: {err}") from err
            await coordinator.async_request_refresh()
        return {"paused": paused}

    hass.services.async_register(DOMAIN, START_MODE, start_mode, schema=START_SCHEMA, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, PAUSE_ALL, pause_all, schema=PAUSE_SCHEMA, supports_response=SupportsResponse.OPTIONAL)
