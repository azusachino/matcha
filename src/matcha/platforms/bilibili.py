"""Bilibili: identity, request descriptions, and pure payload parsers.

Everything here is data in, data out. The bot supplies the HTTP client, the cookies and
the log; this module supplies the URLs that are worth calling and the reading of what
comes back. `x/web-interface/view` is the metadata source (it carries owner, cover,
total duration and `pages[].cid`); `x/player/playurl` with `fnval=4048` is the download
plan (per-stream bandwidth and duration, so size is priced before any byte moves).

Both endpoints answer 412 to an anonymous request without visitor cookies. A caller
that gets 412 has skipped `visitor_session()`.
"""

from __future__ import annotations

import hashlib
import hmac
import re

from ..errors import ApiError, NeedsExpansionError
from ..types import (
    MediaInfo,
    PartInfo,
    Reason,
    Request,
    Session,
    Stream,
    StreamPlan,
    WorkRef,
)
from .base import PlatformSpec

API_BASE = "https://api.bilibili.com"
REFERER = "https://www.bilibili.com/"
ORIGIN = "https://www.bilibili.com"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36"
)
TICKET_URL = f"{API_BASE}/bapis/bilibili.api.ticket.v1.Ticket/GenWebTicket"
TICKET_KEY = b"XgwSnGZ1p"
FNVAL_DASH = 4048
AVC_CODEC_ID = 7

QUALITY_NAMES = {
    16: "360p",
    32: "480p",
    64: "720p",
    74: "720p60",
    80: "1080p",
    112: "1080p+",
    116: "1080p60",
    120: "4K",
    127: "8K",
}


def default_headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT, "Referer": REFERER, "Origin": ORIGIN}


def api_params(ref: WorkRef) -> dict[str, str]:
    """The API identifier: ``bvid`` when the link had one, ``aid`` for legacy ``av`` links."""
    if ref.kind == "episode" or ref.kind == "collection":
        return (
            {"ep_id": ref.work_id.removeprefix("ep")}
            if ref.kind == "episode"
            else {"season_id": ref.work_id.removeprefix("ss")}
        )
    key = "aid" if ref.work_id.startswith("av") else "bvid"
    value = ref.work_id[2:] if key == "aid" else ref.work_id
    return {key: value}


def view_request(ref: WorkRef, session: Session) -> Request:
    return Request(
        "GET",
        f"{API_BASE}/x/web-interface/view",
        tuple(api_params(ref).items()),
        headers=default_headers(),
        cookies=dict(session.cookies),
    )


def playurl_request(ref: WorkRef, session: Session, *, qn: int = 80) -> Request:
    params = {
        **api_params(ref),
        "fnval": str(FNVAL_DASH),
        "fnver": "0",
        "fourk": "1",
        "qn": str(qn),
    }
    if ref.part:
        params["page"] = str(ref.part)
    if "aid" in params:
        params["cid"] = ""  # filled by the caller from view(); keeps the request honest
    return Request(
        "GET",
        f"{API_BASE}/x/player/playurl",
        tuple(params.items()),
        headers=default_headers(),
        cookies=dict(session.cookies),
    )


def spi_request() -> Request:
    """The visitor cookies the site sets on a first visit."""
    return Request("GET", f"{API_BASE}/x/frontend/finger/spi", headers=default_headers())


def ticket_request(ts: int) -> Request:
    """`GenWebTicket`, signed the way the web player signs it."""
    sign = hmac.new(TICKET_KEY, f"ts{ts}".encode(), hashlib.sha256).hexdigest()
    url = f"{TICKET_URL}?key_id=ec02&hexsign={sign}&context[ts]={ts}&csrf="
    return Request("POST", url, headers=default_headers())


def visitor_session(spi_body: dict, ticket_body: dict | None = None) -> dict[str, str]:
    """Cookies from a `/spi` body and an optional ticket body. Missing parts stay missing."""
    data = spi_body.get("data") or {}
    cookies = {k: v for k, v in (("buvid3", data.get("b_3")), ("buvid4", data.get("b_4"))) if v}
    if data.get("b_nut"):
        cookies["b_nut"] = data["b_nut"]
    ticket = ((ticket_body or {}).get("data") or {}).get("ticket")
    if ticket:
        cookies["bili_ticket"] = ticket
    return cookies


def expand_request(ref: WorkRef) -> Request:
    """A b23.tv short link is opaque; resolving it needs one redirect hop."""
    if ref.kind != "short_link":
        raise NeedsExpansionError(f"{ref.work_id} is not a short link")
    return Request("GET", f"https://b23.tv/{ref.work_id}", headers=default_headers())


def _expect_ok(body: dict) -> dict:
    code = body.get("code")
    if code != 0:
        raise ApiError(code, body.get("message") or "")
    return body.get("data") or {}


def parse_view(body: dict, ref: WorkRef, *, canonical: str = "") -> MediaInfo:
    """Read a `view` body. Fields the source omits stay ``None``, never a placeholder."""
    data = _expect_ok(body)
    pages = [
        PartInfo(
            index=int(page.get("page") or index + 1),
            title=str(page.get("part") or ""),
            duration_s=float(page["duration"]) if page.get("duration") else None,
        )
        for index, page in enumerate(data.get("pages") or [])
    ]
    owner = data.get("owner") or {}
    selected = None
    if ref.part and pages:
        selected = next((p for p in pages if p.index == ref.part), None)
    duration = (
        selected.duration_s
        if selected
        else (float(data["duration"]) if data.get("duration") else None)
    )
    pic = data.get("pic")
    return MediaInfo(
        platform="bilibili",
        kind=ref.kind,
        work_id=ref.work_id,
        title=str(data.get("title") or ""),
        part=ref.part,
        creator=str(owner["name"]) if owner.get("name") else None,
        duration_s=duration,
        thumbnail_url=pic if isinstance(pic, str) and pic.startswith("http") else None,
        parts=tuple(pages),
        canonical_url=canonical,
    )


def pick_video_stream(dash: dict) -> Stream:
    streams = dash.get("video") or []
    if not streams:
        raise ApiError(-1, "no video streams")
    avc = [s for s in streams if s.get("codecid") == AVC_CODEC_ID]
    chosen = max(avc or streams, key=lambda s: (s.get("id", 0), s.get("bandwidth", 0)))
    return _stream(chosen)


def pick_audio_stream(dash: dict) -> Stream:
    streams = dash.get("audio") or []
    if not streams:
        raise ApiError(-1, "no audio track")
    return _stream(max(streams, key=lambda s: s.get("bandwidth", 0)))


def _stream(raw: dict) -> Stream:
    base = raw.get("baseUrl") or raw.get("base_url") or ""
    backups = raw.get("backupUrl") or raw.get("backup_url") or []
    return Stream(
        url=base,
        backup_urls=tuple(u for u in backups if u),
        codec=str(raw.get("codecs") or "") or None,
        bandwidth=int(raw.get("bandwidth") or 0),
        width=raw.get("width"),
        height=raw.get("height"),
    )


def parse_playurl(body: dict, *, duration_s: float | None = None) -> StreamPlan:
    """Price a DASH response: the chosen streams plus the bytes they will cost."""
    data = _expect_ok(body)
    dash = data.get("dash") or {}
    video = pick_video_stream(dash)
    audio = pick_audio_stream(dash)
    seconds = float(dash.get("duration") or duration_s or 0)
    estimated = int((video.bandwidth + audio.bandwidth) * seconds / 8) if seconds else 0
    quality = QUALITY_NAMES.get(int(data.get("quality") or 0), "")
    return StreamPlan(
        video=video,
        audio=audio,
        estimated_bytes=estimated,
        quality=quality or f"{video.width}x{video.height}",
        needs_merge=True,
        headers={"Referer": REFERER, "User-Agent": USER_AGENT},
    )


def parse_pagelist(body: dict) -> tuple[PartInfo, ...]:
    """`x/player/pagelist` still answers; `view` already carries the same pages."""
    return tuple(
        PartInfo(
            index=int(page.get("page") or index + 1),
            title=str(page.get("part") or ""),
            duration_s=float(page["duration"]) if page.get("duration") else None,
        )
        for index, page in enumerate(_expect_ok(body).get("pages") or [])
        if isinstance(page, dict)
    )


def describe_error(exc: Exception) -> Reason:
    """Map Bilibili's codes onto the shared reason vocabulary."""
    if isinstance(exc, ApiError):
        return {
            -404: Reason.NOT_FOUND,
            -403: Reason.AUTH_REQUIRED,
            -10403: Reason.PREMIUM_ONLY,
            87008: Reason.PREMIUM_ONLY,
            -412: Reason.RATE_LIMITED,
            -509: Reason.RATE_LIMITED,
        }.get(exc.code, Reason.EXTRACTOR_FAILED)
    return Reason.NETWORK


HOSTS = frozenset({"bilibili.com", "www.bilibili.com", "m.bilibili.com", "b23.tv"})
BV_RE = re.compile(r"BV[0-9A-Za-z]{10}")
AV_RE = re.compile(r"av(\d+)", re.IGNORECASE)
EPISODE_RE = re.compile(r"/bangumi/play/(ep\d+)", re.IGNORECASE)
SEASON_RE = re.compile(r"/bangumi/play/(ss\d+)", re.IGNORECASE)


def _page(params: list[tuple[str, str]]) -> int | None:
    """``?p=1`` is normalised away so a canonical URL always reparses to the same ref."""
    for key, value in params:
        if key == "p" and value.isdigit():
            page = int(value)
            return page if page > 1 else None
    return None


def parse(host: str, path: str, params: list[tuple[str, str]]) -> WorkRef | None:
    if host == "b23.tv":
        short_id = path.strip("/")
        if BV_RE.fullmatch(short_id):
            return WorkRef(
                "bilibili", "part" if _page(params) else "video", short_id, _page(params)
            )
        return WorkRef("bilibili", "short_link", short_id) if short_id else None

    page = _page(params)
    episode = EPISODE_RE.search(path)
    if episode:
        return WorkRef("bilibili", "episode", episode.group(1).lower(), page)
    season = SEASON_RE.search(path)
    if season:
        return WorkRef("bilibili", "collection", season.group(1).lower(), page)
    bv = BV_RE.search(path)
    if bv:
        return WorkRef("bilibili", "part" if page else "video", bv.group(0), page)
    av = AV_RE.search(path)
    if av:
        return WorkRef("bilibili", "part" if page else "video", f"av{av.group(1)}", page)
    return None


def canonical(ref: WorkRef) -> str | None:
    if ref.platform != "bilibili":
        return None
    if ref.kind == "short_link":
        raise NeedsExpansionError(f"b23.tv/{ref.work_id} must be expanded before use")
    if ref.kind in {"episode", "collection"}:
        return f"https://www.bilibili.com/bangumi/play/{ref.work_id}"
    link = f"https://www.bilibili.com/video/{ref.work_id}"
    return f"{link}?p={ref.part}" if ref.part else link


SPEC = PlatformSpec("bilibili", HOSTS, parse, canonical)
