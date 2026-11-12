"""Shared vocabulary: what a link means, what a source reported, what to do with it."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class Reason(StrEnum):
    """Why something got harder. Bots phrase these; they never invent their own."""

    NOT_FOUND = "not_found"
    AUTH_REQUIRED = "auth_required"
    PREMIUM_ONLY = "premium_only"
    REGION_BLOCKED = "region_blocked"
    RATE_LIMITED = "rate_limited"
    TOO_LARGE = "too_large"
    NO_PLAN = "no_plan"
    NO_ACCESS = "no_access"
    MANUAL_POLICY = "manual_policy"
    EXTRACTOR_FAILED = "extractor_failed"
    NETWORK = "network"


@dataclass(frozen=True, slots=True)
class WorkRef:
    """What the user meant, independent of how they pasted it.

    ``part`` is the 1-based Bilibili part (``?p=``); ``start`` is a YouTube start offset
    in seconds. Two pastes of the same part produce equal values, which is what makes
    round-tripping testable.
    """

    platform: str
    kind: str
    work_id: str
    part: int | None = None
    start: int | None = None

    @property
    def is_episode(self) -> bool:
        return self.kind in {"episode", "collection"}


@dataclass(frozen=True, slots=True)
class Session:
    """Cookies a bot already holds for a platform. Opaque to the core."""

    cookies: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Request:
    """A request description. The bot performs it with its own HTTP client.

    Keeping requests as data is what lets one core serve a sync bot and an async bot.
    """

    method: str
    url: str
    params: tuple[tuple[str, str], ...] = ()
    headers: Mapping[str, str] = field(default_factory=dict)
    cookies: Mapping[str, str] = field(default_factory=dict)
    body: str | None = None


@dataclass(frozen=True, slots=True)
class PartInfo:
    index: int
    title: str
    duration_s: float | None = None


@dataclass(frozen=True, slots=True)
class MediaInfo:
    """What the source published.

    ``None`` means the source did not publish it. Renderers must omit the field then;
    printing "Unknown" turns absence into a claim about the creator.
    """

    platform: str
    kind: str
    work_id: str
    title: str
    part: int | None = None
    creator: str | None = None
    duration_s: float | None = None
    width: int | None = None
    height: int | None = None
    thumbnail_url: str | None = None
    parts: tuple[PartInfo, ...] = ()
    canonical_url: str = ""

    @property
    def is_multi_part(self) -> bool:
        return len(self.parts) > 1


@dataclass(frozen=True, slots=True)
class Stream:
    url: str
    backup_urls: tuple[str, ...] = ()
    codec: str | None = None
    bandwidth: int = 0
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True, slots=True)
class StreamPlan:
    """A chosen way to fetch one stream set, priced before any bytes move."""

    video: Stream | None
    audio: Stream | None
    estimated_bytes: int
    quality: str
    needs_merge: bool
    headers: Mapping[str, str] = field(default_factory=dict)

    @property
    def urls(self) -> tuple[str, ...]:
        return tuple(s.url for s in (self.video, self.audio) if s is not None)


@dataclass(frozen=True, slots=True)
class Capabilities:
    """What the destination can take right now (upload limits, preview permission)."""

    max_upload_bytes: int
    preview_allowed: bool = True


@dataclass(frozen=True, slots=True)
class Policy:
    """Per-bot product choices. The pipeline is shared; these values are not.

    suzuran keeps a private library, so it previews nothing automatically, redacts its
    own identifiers too, hides the source link and stores metadata. daphne converts in
    chat, so it previews small files and shows the canonical source.
    """

    auto_preview: bool
    redact_personal: bool = False
    show_source_link: bool = True
    store_metadata: bool = False
    source_label: str = "Source"


@dataclass(frozen=True, slots=True)
class Upload:
    plan: StreamPlan


@dataclass(frozen=True, slots=True)
class Card:
    reason: Reason


Delivery = Upload | Card


@dataclass(frozen=True, slots=True)
class File:
    path: str


@dataclass(frozen=True, slots=True)
class Unavailable:
    why: str


@dataclass(frozen=True, slots=True)
class Failure:
    engine: str
    version: str
    reason: Reason
    detail: str = ""


Outcome = File | Unavailable | Failure


@dataclass(frozen=True, slots=True)
class Attempt:
    engine: str
    version: str
    outcome: Outcome


@dataclass(frozen=True, slots=True)
class ChainResult:
    """Every attempt is kept: an engine that failed is evidence, not noise."""

    path: str
    engine: str
    attempts: tuple[Attempt, ...]
