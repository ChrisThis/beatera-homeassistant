"""The library in the media browser, and songs for other speakers."""

from homeassistant.components import media_source

from custom_components.beatera.browse import browse

from .conftest import API, URL
from .test_init import setup


async def test_the_library_can_be_browsed(hass, server, entry):
    await setup(hass, entry)
    server.get(f"{API}/movies", json={"page": "Library/Grid", "data": {"items": {"data": [{"id": 7, "title": "Alien", "image": {"small": "/artwork/3/300"}}]}}})
    api = entry.runtime_data.api

    root = await browse(api, None)
    assert [child.media_content_id for child in root.children] == ["beatera:section:movies", "beatera:section:series", "beatera:section:albums", "beatera:section:playlists"]
    movies = await browse(api, "beatera:section:movies")
    assert movies.children[0].title == "Alien"
    assert movies.children[0].media_content_id == "beatera:movie:7"
    assert movies.children[0].thumbnail == f"{URL}/artwork/3/300"


async def test_songs_play_on_other_speakers(hass, server, entry):
    await setup(hass, entry)
    assert "media_source" in hass.config.components, "Loaded as a dependency."
    server.get(f"{API}/music/albums", json={"data": {"items": {"data": [{"id": 4, "title": "Innuendo", "subtitle": "Queen"}]}}})
    server.get(f"{API}/albums/4", json={"data": {"title": "Innuendo", "discs": [{"tracks": [{"recordingId": 11, "number": 1, "title": "Innuendo"}]}]}})
    server.post(f"{API}/playback/prepare", json={"kind": "audio", "mode": "direct", "lossless": True, "url": "/media/file/abc"})

    albums = await media_source.async_browse_media(hass, "media-source://beatera")
    assert albums.children[0].title == "Queen – Innuendo"
    tracks = await media_source.async_browse_media(hass, "media-source://beatera/album/4")
    assert tracks.children[0].media_content_id == "media-source://beatera/song/11"
    played = await media_source.async_resolve_media(hass, "media-source://beatera/song/11", None)
    assert played.url == f"{URL}/media/file/abc"
    assert played.mime_type == "audio/flac"
