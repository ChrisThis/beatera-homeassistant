"""Beatera: self-hosted music and video in Home Assistant."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging

from aiohttp import web

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError

from .api import BeateraApi, BeateraAuthError, BeateraError
from .const import CONF_HOOK_ID, CONF_HOOK_SECRET, CONF_TOKEN, CONF_WEBHOOK_ID, DOMAIN, EVENT
from .coordinator import BeateraCoordinator
from .entity import server_device

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.MEDIA_PLAYER, Platform.SENSOR]

type BeateraConfigEntry = ConfigEntry[BeateraCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: BeateraConfigEntry) -> bool:
    api = BeateraApi(async_get_clientsession(hass), entry.data[CONF_URL], entry.data[CONF_TOKEN])
    try:
        me = await api.me()
    except BeateraAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except BeateraError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = BeateraCoordinator(hass, entry, api, me)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    # The players hang below the server.
    dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id, **server_device(coordinator))

    await _async_setup_webhook(hass, entry, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BeateraConfigEntry) -> bool:
    if CONF_WEBHOOK_ID in entry.data:
        webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: BeateraConfigEntry) -> None:
    """Beatera no longer needs to call this Home Assistant."""
    if CONF_HOOK_ID not in entry.data:
        return
    api = BeateraApi(async_get_clientsession(hass), entry.data[CONF_URL], entry.data[CONF_TOKEN])
    try:
        await api.remove_hook(entry.data[CONF_HOOK_ID])
    except BeateraError:
        _LOGGER.debug("Webhook at Beatera could not be removed")


async def _async_setup_webhook(hass: HomeAssistant, entry: BeateraConfigEntry, coordinator: BeateraCoordinator) -> None:
    """Beatera tells at once what happens, when the token may set that up (admin)."""
    data = dict(entry.data)
    webhook_id = data.get(CONF_WEBHOOK_ID) or webhook.async_generate_id()

    async def handle(hass: HomeAssistant, webhook_id: str, request: web.Request) -> web.Response:
        body = await request.read()
        secret = entry.data.get(CONF_HOOK_SECRET)
        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest() if secret else None
        if expected is None or not hmac.compare_digest(expected, request.headers.get("X-Beatera-Signature", "")):
            return web.Response(status=401)
        try:
            message = json.loads(body)
        except ValueError:
            return web.Response(status=400)
        # "event" says what happened (playback.started …), "type" what it is about (movie, episode …).
        hass.bus.async_fire(EVENT, {**(message.get("data") or {}), "event": message.get("event"), "at": message.get("at")})
        await coordinator.async_request_refresh()
        return web.Response(status=200)

    webhook.async_register(hass, DOMAIN, "Beatera", webhook_id, handle, allowed_methods=["POST"])

    if CONF_HOOK_ID not in data and coordinator.admin:
        try:
            url = webhook.async_generate_url(hass, webhook_id, prefer_external=False)
        except NoURLAvailableError:
            _LOGGER.info("Home Assistant knows no address of its own; Beatera is asked regularly instead")
            return
        try:
            hook = await coordinator.api.add_hook("Home Assistant", url)
        except BeateraError as err:
            _LOGGER.warning("Beatera could not set up the webhook: %s", err)
            return
        data.update({CONF_WEBHOOK_ID: webhook_id, CONF_HOOK_ID: hook["id"], CONF_HOOK_SECRET: hook["secret"]})
        hass.config_entries.async_update_entry(entry, data=data)
