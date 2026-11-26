"""Constants of the Beatera integration."""

from datetime import timedelta

DOMAIN = "beatera"

CONF_TOKEN = "token"
CONF_HOOK_ID = "hook_id"
CONF_HOOK_SECRET = "hook_secret"
CONF_WEBHOOK_ID = "webhook_id"

# Polling is the fallback; webhooks make it immediate.
SCAN_INTERVAL = timedelta(seconds=15)

# Fired for everything Beatera reports: playback started, paused, resumed, ended, scan finished, media added.
EVENT = "beatera_event"

# What Beatera can play as a whole on one of its own players.
PLAYABLE = ("movie", "episode", "series", "concert", "video", "recording", "album", "artist", "playlist", "mix")
