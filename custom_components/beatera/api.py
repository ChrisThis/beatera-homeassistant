"""Talks to the Beatera server, only through /api/v1 and a token."""

from __future__ import annotations

from typing import Any

import aiohttp


class BeateraError(Exception):
    """The server could not be reached or gave no sensible answer."""


class BeateraAuthError(BeateraError):
    """The token is wrong, revoked or lacks a right."""


class BeateraApi:
    """A small client: every method is one request."""

    def __init__(self, session: aiohttp.ClientSession, url: str, token: str) -> None:
        self.base = url.rstrip("/")
        self._session = session
        self._token = token

    def absolute(self, path: str | None) -> str | None:
        """Addresses from the server are relative to it."""
        if not path:
            return None
        return path if path.startswith(("http://", "https://")) else f"{self.base}{path}"

    async def request(self, method: str, path: str, json: Any = None, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base}/api/v1{path}"
        headers = {"Accept": "application/json", **({"Authorization": f"Bearer {self._token}"} if self._token else {})}
        try:
            async with self._session.request(method, url, json=json, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as response:
                # A wrong pairing code comes back as 422.
                if response.status in (401, 403) or (response.status == 422 and path == "/pair"):
                    raise BeateraAuthError(f"{method} {path}: HTTP {response.status}")
                if response.status == 204:
                    return None
                if response.status >= 400:
                    raise BeateraError(f"{method} {path}: HTTP {response.status}")
                return await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise BeateraError(f"{method} {path}: {err}") from err

    async def image(self, path: str) -> tuple[bytes, str] | tuple[None, None]:
        """Pictures need the token as well."""
        try:
            async with self._session.get(self.absolute(path), headers={"Authorization": f"Bearer {self._token}"}, timeout=aiohttp.ClientTimeout(total=20)) as response:
                if response.status != 200:
                    return None, None
                return await response.read(), response.headers.get("Content-Type", "image/jpeg")
        except (aiohttp.ClientError, TimeoutError):
            return None, None

    async def pair(self, code: str, name: str) -> dict[str, Any]:
        """Swaps the pairing code from the profile for a token; needs no token itself."""
        return await self.request("POST", "/pair", json={"code": code, "name": name})

    async def me(self) -> dict[str, Any]:
        return await self.request("GET", "/me")

    async def status(self) -> dict[str, Any]:
        return await self.request("GET", "/status")

    async def players(self) -> list[dict[str, Any]]:
        return (await self.request("GET", "/players"))["players"]

    async def command(self, player: str, kind: str, payload: dict[str, Any] | None = None) -> None:
        await self.request("POST", f"/playback/sessions/{player}/command", json={"type": kind, "payload": payload})

    async def play(self, player: str, kind: str, item: int) -> None:
        """Puts something whole into the queue of a player and starts it there."""
        found = await self.request("POST", "/playback/items", json={"type": kind, "id": item, "continue": kind == "series"})
        await self.command(player, "load", {"items": found["items"], "index": found.get("index", 0), "source": "home_assistant"})

    async def announce(self, player: str, sound: bytes, content_type: str, name: str, volume: float | None = None) -> None:
        """Sends a sound or spoken text to Beatera, which the player then plays; afterwards what played goes on."""
        form = aiohttp.FormData()
        form.add_field("sound", sound, filename=name, content_type=content_type)
        try:
            async with self._session.post(
                f"{self.base}/api/v1/announcements", data=form, headers={"Authorization": f"Bearer {self._token}", "Accept": "application/json"}, timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                if response.status in (401, 403):
                    raise BeateraAuthError(f"POST /announcements: HTTP {response.status}")
                if response.status >= 400:
                    raise BeateraError(f"POST /announcements: HTTP {response.status}")
                url = (await response.json(content_type=None))["url"]
        except (aiohttp.ClientError, TimeoutError) as err:
            raise BeateraError(f"POST /announcements: {err}") from err
        await self.command(player, "announce", {"url": url, **({"volume": volume} if volume is not None else {})})

    async def modes(self) -> list[dict[str, Any]]:
        return (await self.request("GET", "/modes"))["modes"]

    async def start_mode(self, mode: int, players: list[str] | None = None, **options: Any) -> list[dict[str, Any]]:
        body = {key: value for key, value in options.items() if value is not None}
        if players:
            body["players"] = players
        return (await self.request("POST", f"/modes/{mode}/start", json=body))["results"]

    async def pause_all(self, players: list[str] | None = None) -> list[str]:
        return (await self.request("POST", "/players/pause", json={"players": players} if players else {}))["paused"]

    async def page(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """The data of a page of the web interface."""
        return (await self.request("GET", path, params=params))["data"]

    async def prepare(self, kind: str, item: int) -> dict[str, Any]:
        return await self.request("POST", "/playback/prepare", json={"type": kind, "id": item})

    async def start_scan(self) -> None:
        await self.request("POST", "/admin/scanner/scan")

    async def add_hook(self, name: str, url: str) -> dict[str, Any]:
        return await self.request("POST", "/admin/webhooks", json={"name": name, "url": url})

    async def remove_hook(self, hook: int) -> None:
        await self.request("DELETE", f"/admin/webhooks/{hook}")
