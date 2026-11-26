"""Music from Beatera on every other player of Home Assistant (Sonos, Chromecast, …).

These players fetch a single address, so only songs are offered: the file itself, or a
smaller copy when the original is something they rarely understand.
"""

from __future__ import annotations

from homeassistant.components.media_player import BrowseError, MediaClass, MediaType
from homeassistant.components.media_source import BrowseMediaSource, MediaSource, MediaSourceItem, PlayMedia, Unresolvable
from homeassistant.core import HomeAssistant

from .api import BeateraError
from .const import DOMAIN


async def async_get_media_source(hass: HomeAssistant) -> MediaSource:
    return BeateraSource(hass)


class BeateraSource(MediaSource):
    name = "Beatera"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass

    def _api(self):
        entries = [entry for entry in self.hass.config_entries.async_entries(DOMAIN) if getattr(entry, "runtime_data", None) is not None]
        if not entries:
            raise BrowseError("Beatera is not set up")
        return entries[0].runtime_data.api

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        kind, _, key = item.identifier.partition("/")
        if kind != "song" or not key.isdigit():
            raise Unresolvable(f"Not a song: {item.identifier}")
        api = self._api()
        try:
            prepared = await api.prepare("recording", int(key))
        except BeateraError as err:
            raise Unresolvable(str(err)) from err
        lossless = prepared.get("lossless") and prepared.get("mode") == "direct"
        return PlayMedia(api.absolute(prepared["url"]), "audio/flac" if lossless else "audio/mpeg")

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        api = self._api()
        kind, _, key = (item.identifier or "").partition("/")
        try:
            if kind == "album" and key.isdigit():
                data = await api.page(f"/albums/{key}")
                tracks = [track for disc in data.get("discs", []) for track in disc.get("tracks", [])]
                return self._folder(f"album/{key}", data.get("title") or "Album", MediaClass.ALBUM, [
                    BrowseMediaSource(domain=DOMAIN, identifier=f"song/{track['recordingId']}", media_class=MediaClass.TRACK, media_content_type=MediaType.MUSIC,
                                      title=f"{track.get('number') or ''} {track.get('title')}".strip(), can_play=True, can_expand=False)
                    for track in tracks
                ])
            data = await api.page("/music/albums", {"sort": "recent"})
        except BeateraError as err:
            raise BrowseError(str(err)) from err
        return self._folder("", "Beatera", MediaClass.DIRECTORY, [
            BrowseMediaSource(domain=DOMAIN, identifier=f"album/{album['id']}", media_class=MediaClass.ALBUM, media_content_type=MediaType.ALBUM,
                              title=" – ".join(filter(None, [album.get("subtitle"), album.get("title")])), can_play=False, can_expand=True,
                              thumbnail=api.absolute((album.get("image") or {}).get("small")))
            for album in (data.get("items") or {}).get("data", [])[:200]
        ])

    @staticmethod
    def _folder(identifier: str, title: str, media_class: str, children: list[BrowseMediaSource]) -> BrowseMediaSource:
        return BrowseMediaSource(domain=DOMAIN, identifier=identifier, media_class=media_class, media_content_type=MediaType.MUSIC, title=title,
                                 can_play=False, can_expand=True, children=children, children_media_class=MediaClass.TRACK if media_class == MediaClass.ALBUM else MediaClass.ALBUM)
