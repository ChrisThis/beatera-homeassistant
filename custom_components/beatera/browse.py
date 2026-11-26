"""The library of Beatera as a tree for the media browser of Home Assistant."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import BrowseError, BrowseMedia, MediaClass, MediaType

from .api import BeateraApi, BeateraError

# Shown at the top; the path is the page of the API, kind the type to play.
SECTIONS = {
    "movies": ("/movies", "movie", MediaClass.MOVIE, "Filme · Movies"),
    "series": ("/series", "series", MediaClass.TV_SHOW, "Serien · Series"),
    "albums": ("/music/albums", "album", MediaClass.ALBUM, "Alben · Albums"),
    "playlists": ("/my/playlists", "playlist", MediaClass.PLAYLIST, "Playlists"),
}

ROOT = "beatera:root"


def media_id(kind: str, item: int | str) -> str:
    return f"beatera:{kind}:{item}"


def parse(value: str) -> tuple[str, str]:
    """beatera:<kind>:<id> → (kind, id)."""
    parts = value.split(":", 2)
    if len(parts) != 3 or parts[0] != "beatera":
        raise BrowseError(f"Unknown media: {value}")
    return parts[1], parts[2]


async def browse(api: BeateraApi, value: str | None) -> BrowseMedia:
    if value in (None, ROOT):
        return BrowseMedia(
            title="Beatera", media_class=MediaClass.DIRECTORY, media_content_id=ROOT, media_content_type="beatera", can_play=False, can_expand=True,
            children=[
                BrowseMedia(title=title, media_class=MediaClass.DIRECTORY, media_content_id=media_id("section", key), media_content_type="beatera", can_play=False, can_expand=True, children_media_class=media_class)
                for key, (_, _, media_class, title) in SECTIONS.items()
            ],
        )
    kind, key = parse(value)
    if kind != "section" or key not in SECTIONS:
        raise BrowseError(f"Cannot open {value}")
    path, play_kind, media_class, title = SECTIONS[key]
    try:
        data = await api.page(path, {"sort": "recent"} if key != "playlists" else None)
    except BeateraError as err:
        raise BrowseError(str(err)) from err
    items: list[dict[str, Any]] = data.get("playlists") if key == "playlists" else (data.get("items") or {}).get("data", [])
    return BrowseMedia(
        title=title, media_class=MediaClass.DIRECTORY, media_content_id=value, media_content_type="beatera", can_play=False, can_expand=True, children_media_class=media_class,
        children=[
            BrowseMedia(
                title=item.get("title") or item.get("name") or "?", media_class=media_class, media_content_id=media_id(play_kind, item["id"]),
                media_content_type=MediaType.MUSIC if play_kind in ("album", "playlist") else MediaType.VIDEO, can_play=True, can_expand=False,
                thumbnail=api.absolute(((item.get("image") or {}).get("small")) if isinstance(item.get("image"), dict) else None),
            )
            for item in (items or [])[:200]
            if "id" in item
        ],
    )
