"""Setting up with address and key."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.const import CONF_URL
from homeassistant.data_entry_flow import FlowResultType

from custom_components.beatera.const import CONF_TOKEN, DOMAIN

from .conftest import API, ME, URL


async def test_set_up_with_address_and_key(hass, aioclient_mock):
    aioclient_mock.get(f"{API}/me", json=ME)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: "ftp://x", CONF_TOKEN: "1|abc"})
    assert result["errors"] == {CONF_URL: "invalid_url"}

    # Only the dialog here; setting up is tested elsewhere.
    with patch("custom_components.beatera.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL + "/", CONF_TOKEN: " 1|abc "})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Beatera (Chris)"
    assert result["data"] == {CONF_URL: URL, CONF_TOKEN: "1|abc"}
    assert aioclient_mock.mock_calls[-1][3]["Authorization"] == "Bearer 1|abc"


async def test_wrong_key_and_too_few_rights(hass, aioclient_mock):
    aioclient_mock.get(f"{API}/me", status=401)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER}, data={CONF_URL: URL, CONF_TOKEN: "x"})
    assert result["errors"] == {"base": "invalid_auth"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{API}/me", json={**ME, "scopes": ["read"]})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER}, data={CONF_URL: URL, CONF_TOKEN: "x"})
    assert result["errors"] == {"base": "missing_rights"}
