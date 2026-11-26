"""Every Beatera player that is online (app, browser, television) as a media player."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.media_player import (
    BrowseMedia,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BeateraConfigEntry
from .api import BeateraError
from .browse import browse, parse
from .const import DOMAIN, PLAYABLE
from .coordinator import BeateraCoordinator

FEATURES = (
    MediaPlayerEntityFeature.PLAY | MediaPlayerEntityFeature.PAUSE | MediaPlayerEntityFeature.STOP | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK | MediaPlayerEntityFeature.SEEK | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.PLAY_MEDIA | MediaPlayerEntityFeature.BROWSE_MEDIA
)

VIDEO = {"movie", "episode", "concert", "video", "live"}


async def async_setup_entry(hass: HomeAssistant, entry: BeateraConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def appear() -> None:
        """Players come and go with the apps and browsers that are open."""
        new = [player for player in coordinator.data.players if player not in known]
        known.update(new)
        if new:
            add(BeateraPlayer(coordinator, player) for player in new)

    appear()
    entry.async_on_unload(coordinator.async_add_listener(appear))


class BeateraPlayer(CoordinatorEntity[BeateraCoordinator], MediaPlayerEntity):
    _attr_has_entity_name = True
    _attr_supported_features = FEATURES
    _attr_media_image_remotely_accessible = False

    def __init__(self, coordinator: BeateraCoordinator, player: str) -> None:
        super().__init__(coordinator)
        self._player = player
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}-{player}"
        self._attr_name = None
        state = coordinator.data.players[player]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, player)},
            "name": state.get("name") or "Beatera",
            "manufacturer": "Beatera",
            "model": state.get("device") or "Player",
            "via_device": (DOMAIN, coordinator.config_entry.entry_id),
        }

    @property
    def _state(self) -> dict[str, Any] | None:
        return self.coordinator.data.players.get(self._player)

    @property
    def _item(self) -> dict[str, Any]:
        return (self._state or {}).get("item") or {}

    @property
    def available(self) -> bool:
        return super().available and self._state is not None

    @property
    def state(self) -> MediaPlayerState | None:
        state = self._state
        if state is None:
            return None
        if state.get("playing"):
            return MediaPlayerState.PLAYING
        return MediaPlayerState.PAUSED if self._item else MediaPlayerState.IDLE

    @property
    def media_content_id(self) -> str | None:
        return f"beatera:{self._item['type']}:{self._item['id']}" if self._item.get("type") else None

    @property
    def media_content_type(self) -> str | None:
        kind = self._item.get("type")
        if kind is None:
            return None
        return {"movie": MediaType.MOVIE, "episode": MediaType.TVSHOW, "radio": MediaType.CHANNEL, "live": MediaType.CHANNEL}.get(kind, MediaType.VIDEO if kind in VIDEO else MediaType.MUSIC)

    @property
    def media_title(self) -> str | None:
        return self._item.get("title")

    @property
    def media_artist(self) -> str | None:
        return None if self._item.get("type") in VIDEO else self._item.get("subtitle")

    @property
    def media_series_title(self) -> str | None:
        return self._item.get("subtitle") if self._item.get("type") == "episode" else None

    @property
    def media_image_url(self) -> str | None:
        return self._item.get("image")

    @property
    def media_duration(self) -> int | None:
        duration = (self._state or {}).get("duration") or 0
        return round(duration / 1000) if duration > 0 else None

    @property
    def media_position(self) -> int | None:
        return round(((self._state or {}).get("position") or 0) / 1000) if self._item else None

    @property
    def media_position_updated_at(self) -> datetime | None:
        reported = (self._state or {}).get("reportedAt")
        return datetime.fromtimestamp(reported / 1000, tz=timezone.utc) if reported else None

    @property
    def volume_level(self) -> float | None:
        return (self._state or {}).get("volume")

    async def async_get_media_image(self) -> tuple[bytes | None, str | None]:
        path = self.media_image_url
        return await self.coordinator.api.image(path) if path else (None, None)

    async def _send(self, kind: str, payload: dict[str, Any] | None = None) -> None:
        try:
            await self.coordinator.api.command(self._player, kind, payload)
        except BeateraError as err:
            raise HomeAssistantError(f"Beatera: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_media_play(self) -> None:
        await self._send("play")

    async def async_media_pause(self) -> None:
        await self._send("pause")

    async def async_media_stop(self) -> None:
        await self._send("stop")

    async def async_media_next_track(self) -> None:
        await self._send("next")

    async def async_media_previous_track(self) -> None:
        await self._send("previous")

    async def async_media_seek(self, position: float) -> None:
        await self._send("seek", {"position": int(position * 1000)})

    async def async_set_volume_level(self, volume: float) -> None:
        await self._send("volume", {"volume": round(volume, 3)})

    async def async_play_media(self, media_type: str, media_id: str, **kwargs: Any) -> None:
        """beatera:<type>:<id>, as given by the media browser."""
        kind, item = parse(media_id)
        if kind not in PLAYABLE or not item.isdigit():
            raise HomeAssistantError(f"Beatera cannot play {media_id}")
        try:
            await self.coordinator.api.play(self._player, kind, int(item))
        except BeateraError as err:
            raise HomeAssistantError(f"Beatera: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_browse_media(self, media_content_type: str | None = None, media_content_id: str | None = None) -> BrowseMedia:
        return await browse(self.coordinator.api, media_content_id)
