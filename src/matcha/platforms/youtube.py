"""YouTube: identity only. Fetching stays with yt-dlp in the bots."""

from __future__ import annotations

import re

from ..types import WorkRef
from .base import Params, PlatformSpec

HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"})
ID_RE = re.compile(r"[A-Za-z0-9_-]{11}")
START_RE = re.compile(r"(?:(\d+)h)?(?:(\d+)m)?(\d+)s?")


def _start(value: str) -> int | None:
    match = START_RE.fullmatch(value)
    if not match or not any(match.groups()):
        return None
    hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def parse(host: str, path: str, params: Params) -> WorkRef | None:
    values = dict(params)
    start = _start(values["t"]) if values.get("t") else None
    if host == "youtu.be":
        candidate = path.strip("/").split("/")[0]
    elif values.get("v"):
        candidate = values["v"]
    else:
        segments = [s for s in path.split("/") if s]
        candidate = (
            segments[1] if len(segments) > 1 and segments[0] in {"shorts", "embed", "live"} else ""
        )
    if not candidate or not ID_RE.fullmatch(candidate):
        return None
    return WorkRef("youtube", "video", candidate, start=start)


def canonical(ref: WorkRef) -> str | None:
    if ref.platform != "youtube":
        return None
    link = f"https://www.youtube.com/watch?v={ref.work_id}"
    return f"{link}&t={ref.start}" if ref.start else link


SPEC = PlatformSpec("youtube", HOSTS, parse, canonical)
