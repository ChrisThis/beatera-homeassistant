"""Setting up: the address of Beatera and a key from its profile page."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_URL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BeateraApi, BeateraAuthError, BeateraError
from .const import CONF_TOKEN, DOMAIN


class BeateraConfigFlow(ConfigFlow, domain=DOMAIN):
    """One entry for each Beatera account."""

    VERSION = 1

    async def _check(self, url: str, token: str) -> tuple[dict[str, Any] | None, str | None]:
        try:
            me = await BeateraApi(async_get_clientsession(self.hass), url, token).me()
        except BeateraAuthError:
            return None, "invalid_auth"
        except BeateraError:
            return None, "cannot_connect"
        if not {"read", "play"} <= set(me.get("scopes") or []):
            return None, "missing_rights"
        return me, None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip().rstrip("/")
            if urlparse(url).scheme not in ("http", "https"):
                errors[CONF_URL] = "invalid_url"
            else:
                me, error = await self._check(url, user_input[CONF_TOKEN].strip())
                if error:
                    errors["base"] = error
                else:
                    await self.async_set_unique_id(f"{urlparse(url).netloc}-{me['user']['id']}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title=f"Beatera ({me['user']['name']})", data={CONF_URL: url, CONF_TOKEN: user_input[CONF_TOKEN].strip()})
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_URL, default=(user_input or {}).get(CONF_URL, "https://")): str, vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """A new key when the old one was revoked."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            _, error = await self._check(entry.data[CONF_URL], user_input[CONF_TOKEN].strip())
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_TOKEN: user_input[CONF_TOKEN].strip()})
        return self.async_show_form(step_id="reauth_confirm", data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}), errors=errors)
