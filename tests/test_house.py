"""Pairing code, modes, pausing everything, announcements, devices of the household."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.components.media_player import ATTR_MEDIA_ANNOUNCE, ATTR_MEDIA_CONTENT_ID, ATTR_MEDIA_CONTENT_TYPE, DOMAIN as MP
from homeassistant.const import ATTR_ENTITY_ID, CONF_URL
from homeassistant.data_entry_flow import FlowResultType

from custom_components.beatera.const import CONF_TOKEN, DOMAIN

from .conftest import API, ME, OTHER, PLAYER, URL
from .test_init import PLAYER_ENTITY, setup

OTHER_ENTITY = "media_player.anna_safari_ios"


def bodies(server, ending):
    return [call[2] for call in server.mock_calls if str(call[1]).endswith(ending)]


async def test_set_up_with_a_pairing_code(hass, aioclient_mock):
    aioclient_mock.post(f"{API}/pair", json={"token": "7|neu", "scopes": ME["scopes"], "user": ME["user"]})
    aioclient_mock.get(f"{API}/me", json=ME)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    with patch("custom_components.beatera.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL, CONF_TOKEN: " abcd-ef23 "})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_URL: URL, CONF_TOKEN: "7|neu"}
    pair = [call for call in aioclient_mock.mock_calls if str(call[1]).endswith("/pair")][0]
    assert pair[2]["code"] == "abcd-ef23"
    assert "Authorization" not in (pair[3] or {})


async def test_a_wrong_pairing_code(hass, aioclient_mock):
    aioclient_mock.post(f"{API}/pair", status=422)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER}, data={CONF_URL: URL, CONF_TOKEN: "ABCD-EF23"})
    assert result["errors"] == {"base": "invalid_code"}


async def test_devices_of_the_household_carry_the_name_of_their_owner(hass, server, entry):
    await setup(hass, entry)
    state = hass.states.get(OTHER_ENTITY)
    assert state is not None
    assert state.attributes["user"] == "Anna"
    assert hass.states.get(PLAYER_ENTITY).attributes["user"] == "Chris"


async def test_modes_start_by_button_and_by_action(hass, server, entry):
    server.post(f"{API}/modes/4/start", json={"results": [{"player": PLAYER["id"], "name": PLAYER["name"], "result": "started"}]})
    await setup(hass, entry)
    button = [s.entity_id for s in hass.states.async_all("button") if "romantik" in s.entity_id]
    assert button, [s.entity_id for s in hass.states.async_all("button")]
    await hass.services.async_call("button", "press", {ATTR_ENTITY_ID: button[0]}, blocking=True)
    assert bodies(server, "/modes/4/start")[0] in (None, {})

    response = await hass.services.async_call(
        DOMAIN, "start_mode", {"mode": "romantik", ATTR_ENTITY_ID: [PLAYER_ENTITY, OTHER_ENTITY], "volume": 40, "when_playing": "append"}, blocking=True, return_response=True,
    )
    assert response["results"][0]["result"] == "started"
    body = bodies(server, "/modes/4/start")[1]
    assert body["players"] == [PLAYER["id"], OTHER["id"]]
    assert (body["volume"], body["busy"]) == (0.4, "append")


async def test_pause_everything_and_announce(hass, server, entry):
    server.post(f"{API}/players/pause", json={"paused": [PLAYER["id"]]})
    server.post(f"{API}/playback/sessions/{PLAYER['id']}/command", status=204)
    await setup(hass, entry)
    response = await hass.services.async_call(DOMAIN, "pause_all", {}, blocking=True, return_response=True)
    assert response == {"paused": [PLAYER["id"]]}

    server.get("http://ha.test:8123/api/tts_proxy/abc.mp3", content=b"ID3 Ton", headers={"Content-Type": "audio/mpeg"})
    signed = "/announcements/0f6b6d2e-1c1f-4c7a-9d5e-000000000009.mp3?expires=1&signature=x"
    server.post(f"{API}/announcements", json={"url": signed})
    await hass.services.async_call(
        MP, "play_media", {ATTR_ENTITY_ID: PLAYER_ENTITY, ATTR_MEDIA_CONTENT_ID: "/api/tts_proxy/abc.mp3", ATTR_MEDIA_CONTENT_TYPE: "music", ATTR_MEDIA_ANNOUNCE: True}, blocking=True,
    )
    # Home Assistant sends the sound itself; the player fetches it from Beatera.
    assert any(str(call[1]).endswith("/announcements") for call in server.mock_calls)
    sent = bodies(server, "/command")[-1]
    assert sent["type"] == "announce"
    assert sent["payload"]["url"] == signed
