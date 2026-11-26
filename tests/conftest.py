"""A Beatera server that answers from fixed data."""

from __future__ import annotations

import pytest

from homeassistant.const import CONF_URL

from custom_components.beatera.const import CONF_TOKEN, DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry

URL = "http://beatera.test"
API = f"{URL}/api/v1"

ME = {"user": {"id": 1, "name": "Chris", "admin": True}, "scopes": ["read", "play", "write", "admin"]}
STATUS = {"version": "0.16.0", "files": {"movies": 12, "mp3": 30}, "playing": 1, "streams": 0, "scanning": False, "lastScan": None, "work": 3}
PLAYER = {
    "id": "0f6b6d2e-1c1f-4c7a-9d5e-000000000001", "name": "Firefox · Linux", "device": "desktop", "playing": True, "status": "playing",
    "item": {"type": "movie", "id": 7, "title": "Alien", "subtitle": "1979", "image": "/api/v1/artwork/3/300"},
    "position": 61000, "duration": 7000000, "volume": 0.5, "reportedAt": 1764140000000, "seenAt": "2026-11-26T08:00:00Z",
    "user": {"id": 1, "name": "Chris", "own": True},
}
OTHER = {**PLAYER, "id": "0f6b6d2e-1c1f-4c7a-9d5e-000000000002", "name": "Safari · iOS", "playing": False, "user": {"id": 2, "name": "Anna", "own": False}}
MODE = {"id": 4, "name": "Romantik", "content": "playlist", "shuffle": True, "volume": 0.3, "fade": 10, "busy": "replace", "players": []}


@pytest.fixture(autouse=True)
def auto_enable(enable_custom_integrations):
    yield


@pytest.fixture
def server(aioclient_mock):
    aioclient_mock.get(f"{API}/me", json=ME)
    aioclient_mock.get(f"{API}/status", json=STATUS)
    aioclient_mock.get(f"{API}/players", json={"players": [PLAYER, OTHER]})
    aioclient_mock.get(f"{API}/modes", json={"modes": [MODE]})
    aioclient_mock.post(f"{API}/admin/webhooks", json={"id": 5, "secret": "s" * 40, "events": []})
    return aioclient_mock


@pytest.fixture
def entry(hass):
    entry = MockConfigEntry(domain=DOMAIN, title="Beatera (Chris)", unique_id="beatera.test-1", data={CONF_URL: URL, CONF_TOKEN: "1|abc"})
    entry.add_to_hass(hass)
    return entry
