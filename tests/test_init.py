"""Players, sensors, scan and events."""

import hashlib
import hmac
import json

from homeassistant.components.media_player import ATTR_MEDIA_CONTENT_ID, ATTR_MEDIA_CONTENT_TYPE, ATTR_MEDIA_SEEK_POSITION, DOMAIN as MP
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID

from custom_components.beatera.const import CONF_HOOK_ID, CONF_HOOK_SECRET, CONF_WEBHOOK_ID, EVENT
from pytest_homeassistant_custom_component.common import async_capture_events

from .conftest import API, PLAYER

PLAYER_ENTITY = "media_player.firefox_linux"


async def setup(hass, entry):
    await hass.config.async_update(internal_url="http://ha.test:8123")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_players_and_sensors_appear(hass, server, entry):
    await setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED

    state = hass.states.get(PLAYER_ENTITY)
    assert state.state == "playing"
    assert state.attributes["media_title"] == "Alien"
    assert state.attributes["media_position"] == 61
    assert state.attributes["volume_level"] == 0.5

    assert hass.states.get("sensor.beatera_chris_mediendateien") or hass.states.get("sensor.beatera_chris_media_files")
    files = [s for s in hass.states.async_all("sensor") if s.attributes.get("mp3") == 30]
    assert files and files[0].state == "42"
    assert any(s.entity_id.startswith("button.") for s in hass.states.async_all("button"))


async def test_commands_reach_the_player(hass, server, entry):
    await setup(hass, entry)
    url = f"{API}/playback/sessions/{PLAYER['id']}/command"
    server.post(url, status=204)
    server.post(f"{API}/playback/items", json={"items": [{"type": "album", "id": 9}], "index": 0})

    await hass.services.async_call(MP, "media_pause", {ATTR_ENTITY_ID: PLAYER_ENTITY}, blocking=True)
    await hass.services.async_call(MP, "media_seek", {ATTR_ENTITY_ID: PLAYER_ENTITY, ATTR_MEDIA_SEEK_POSITION: 90}, blocking=True)
    await hass.services.async_call(MP, "play_media", {ATTR_ENTITY_ID: PLAYER_ENTITY, ATTR_MEDIA_CONTENT_ID: "beatera:album:9", ATTR_MEDIA_CONTENT_TYPE: "music"}, blocking=True)

    sent = [(call[1].path, call[2]) for call in server.mock_calls if str(call[1]).endswith("/command")]
    assert [body["type"] for _, body in sent] == ["pause", "seek", "load"]
    assert sent[1][1]["payload"] == {"position": 90000}
    assert sent[2][1]["payload"]["items"] == [{"type": "album", "id": 9}]
    assert sent[2][1]["payload"]["source"] == "home_assistant"


async def test_beatera_tells_what_happens(hass, server, entry, hass_client_no_auth):
    await setup(hass, entry)
    assert entry.data[CONF_HOOK_ID] == 5
    registered = [call for call in server.mock_calls if str(call[1]).endswith("/admin/webhooks")]
    assert registered[0][2]["url"] == f"http://ha.test:8123/api/webhook/{entry.data[CONF_WEBHOOK_ID]}"

    events = async_capture_events(hass, EVENT)
    client = await hass_client_no_auth()
    body = json.dumps({"event": "playback.started", "at": "2026-11-26T20:00:00+01:00", "data": {"user": "Chris", "type": "movie", "id": 7, "title": "Alien"}}).encode()
    path = f"/api/webhook/{entry.data[CONF_WEBHOOK_ID]}"

    assert (await client.post(path, data=body, headers={"X-Beatera-Signature": "sha256=falsch"})).status == 401
    signature = "sha256=" + hmac.new(entry.data[CONF_HOOK_SECRET].encode(), body, hashlib.sha256).hexdigest()
    assert (await client.post(path, data=body, headers={"X-Beatera-Signature": signature})).status == 200
    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data["event"] == "playback.started"
    assert events[0].data["type"] == "movie"
    assert events[0].data["title"] == "Alien"


async def test_a_revoked_key_asks_for_a_new_one(hass, aioclient_mock, entry):
    aioclient_mock.get(f"{API}/me", status=401)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert any(flow["context"]["source"] == "reauth" for flow in hass.config_entries.flow.async_progress())
