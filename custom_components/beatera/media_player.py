"""Every Beatera player that is online (app, browser, television) as a media player."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import aiohttp

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    ATTR_MEDIA_ANNOUNCE,
    BrowseMedia,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    async_process_play_media_url,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
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
    | MediaPlayerEntityFeature.PLAY_MEDIA | MediaPlayerEntityFeature.BROWSE_MEDIA | MediaPlayerEntityFeature.MEDIA_ANNOUNCE
)

VIDEO = {"movie", "episode", "concert", "video", "live"}

# What Beatera takes for one announcement.
MAX_SOUND = 10 * 1024 * 1024


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
        owner = state.get("user") or {}
        # Devices of other people in the household carry their name.
        name = state.get("name") or "Beatera"
        if owner and not owner.get("own", True) and owner.get("name"):
            name = f"{owner['name']} · {name}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, player)},
            "name": name,
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
    def extra_state_attributes(self) -> dict[str, Any]:
        owner = (self._state or {}).get("user") or {}
        return {"user": owner.get("name")} if owner.get("name") else {}

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
        """beatera:<type>:<id>, as given by the media browser; sounds and spoken text as an announcement."""
        # Beatera's own entries under Media are played as a whole, not as a sound.
        own = f"media-source://{DOMAIN}/"
        if media_id.startswith(own) and not kwargs.get(ATTR_MEDIA_ANNOUNCE):
            kind, _, key = media_id.removeprefix(own).partition("/")
            media_id = f"beatera:{'recording' if kind == 'song' else kind}:{key}"
        if kwargs.get(ATTR_MEDIA_ANNOUNCE) or not media_id.startswith("beatera:"):
            await self._announce(media_id, kwargs.get(ATTR_MEDIA_ANNOUNCE, True))
            return
        kind, item = parse(media_id)
        if kind not in PLAYABLE or not item.isdigit():
            raise HomeAssistantError(f"Beatera cannot play {media_id}")
        try:
            await self.coordinator.api.play(self._player, kind, int(item))
        except BeateraError as err:
            raise HomeAssistantError(f"Beatera: {err}") from err
        await self.coordinator.async_request_refresh()

    async def _announce(self, media_id: str, announce: bool | None) -> None:
        """Home Assistant fetches the sound and sends it to Beatera; the browser of the player cannot always reach Home Assistant."""
        if media_source.is_media_source_id(media_id):
            media_id = (await media_source.async_resolve_media(self.hass, media_id, self.entity_id)).url
        if not media_id.startswith(("http://", "https://", "/")):
            raise HomeAssistantError(f"Beatera cannot play {media_id}")
        url = async_process_play_media_url(self.hass, media_id)
        try:
            async with async_get_clientsession(self.hass).get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                sound = await response.content.read(MAX_SOUND + 1)
                kind = response.headers.get("Content-Type", "audio/mpeg").split(";")[0]
        except (aiohttp.ClientError, TimeoutError) as err:
            raise HomeAssistantError(f"Beatera: the sound could not be fetched: {err}") from err
        if len(sound) > MAX_SOUND:
            raise HomeAssistantError("Beatera: the sound is longer than 10 MB")
        name = "sound." + {"audio/wav": "wav", "audio/x-wav": "wav", "audio/ogg": "ogg", "audio/flac": "flac", "audio/mp4": "m4a", "audio/aac": "aac", "audio/webm": "webm", "audio/opus": "opus"}.get(kind, "mp3")
        try:
            await self.coordinator.api.announce(self._player, sound, kind, name)
        except BeateraError as err:
            raise HomeAssistantError(f"Beatera: {err}") from err

    async def async_browse_media(self, media_content_type: str | None = None, media_content_id: str | None = None) -> BrowseMedia:
        return await browse(self.coordinator.api, media_content_id)
