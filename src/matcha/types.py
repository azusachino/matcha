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
    """One part (page) of a work, as the source published it.

    ``cid`` is the part's player id, the identifier ``playurl`` and the danmaku endpoints
    actually address. It stays ``None`` when the source omitted it, so a caller that
    needs one treats that as "no plan", not as zero.
    """

    index: int
    title: str
    duration_s: float | None = None
    cid: int | None = None


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
    tracks: tuple[Track, ...] = ()
    # The body's own top-level ``cid``, when it published one. It names part 1 whatever
    # part was asked for (measured: a ``?p=2`` link still carries part 1's cid here), so
    # :attr:`cid` uses it only for a body that published no pages at all.
    body_cid: int | None = None

    @property
    def is_multi_part(self) -> bool:
        return len(self.parts) > 1

    @property
    def selected_part(self) -> PartInfo | None:
        """The page this info is about, so a caller needs no second read of the body.

        With no part selected, that is the body's first page. With ``part`` set, it is
        that page -- and ``None`` when the body does not publish it, never a silent page
        1. ``parse_view`` reads its duration from the same page.
        """
        if not self.parts:
            return None
        if self.part is None:
            return self.parts[0]
        return next((page for page in self.parts if page.index == self.part), None)

    @property
    def cid(self) -> int | None:
        """The cid ``playurl_request`` needs: the selected part's, or the body's own.

        A body that published no pages at all falls back to its top-level ``cid``, since
        that is the only cid it offers. Once a page exists the fallback is never used:
        that cid belongs to part 1 even when another part was selected.
        """
        if not self.parts:
            return self.body_cid
        part = self.selected_part
        return None if part is None else part.cid


class TrackKind(StrEnum):
    """What a sidecar file is. Conversion to a playable format stays in the bot.

    A kind belongs here once a parser under ``platforms/`` produces it; vocabulary that
    nothing produces yet is listed in :data:`RESERVED_TRACK_KINDS`. That list documents
    intent -- it is not enforced, so a branch on a reserved kind still type-checks and
    runs. Check it before relying on a kind arriving.
    """

    SUBTITLE = "subtitle"
    DANMAKU = "danmaku"
    CHAPTERS = "chapters"
    THUMBNAIL = "thumbnail"


#: Kinds no parser produces yet: **documentary, not enforced**. The members still exist
#: and still construct, so nothing fails if a bot branches on one; this list only separates
#: committed vocabulary from planned vocabulary, and a test guards that the parsers stay
#: out of it. ``CHAPTERS`` is reserved because chapter markers arrive inline in a player
#: body, not as a downloadable sidecar URL. ``THUMBNAIL`` is reserved because a work's
#: cover already has exactly one home, :attr:`MediaInfo.thumbnail_url`; the kind would only
#: name a cover *sidecar* file, which no parser describes.
RESERVED_TRACK_KINDS: frozenset[TrackKind] = frozenset({TrackKind.CHAPTERS, TrackKind.THUMBNAIL})


@dataclass(frozen=True, slots=True)
class Track:
    """A sidecar the source published next to the media.

    ``lang`` is the source's own label (``zh-CN``, ``ai-zh``) and stays ``None`` when
    the source omitted it. ``format`` names the wire format (``json``, ``xml``,
    ``protobuf``) so the bot can pick a converter without sniffing bytes. It is the
    source's published field when there is one, and an inference otherwise: a Bilibili
    subtitle entry that omits ``format`` is labelled ``json`` because its URL ends in
    ``.json`` -- an inference, not a published field.
    """

    url: str
    lang: str | None = None
    format: str | None = None
    kind: TrackKind = TrackKind.SUBTITLE


@dataclass(frozen=True, slots=True)
class Stream:
    url: str
    backup_urls: tuple[str, ...] = ()
    codec: str | None = None
    bandwidth: int = 0
    width: int | None = None
    height: int | None = None
    quality_id: int | None = None


@dataclass(frozen=True, slots=True)
class StreamPlan:
    """A chosen way to fetch one stream set, priced before any bytes move."""

    video: Stream | None
    audio: Stream | None
    estimated_bytes: int
    quality: str
    needs_merge: bool
    headers: Mapping[str, str] = field(default_factory=dict)
    tracks: tuple[Track, ...] = ()

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

    ``auto_preview`` is the one *delivery* decision. ``None`` means this policy has not
    made it -- which is what a policy built for selection or naming looks like. Selection
    and naming never read it; :func:`matcha.deliver.decide` refuses it rather than turn an
    unstated decision into a card.
    """

    auto_preview: bool | None = None
    redact_personal: bool = False
    show_source_link: bool = True
    store_metadata: bool = False
    source_label: str = "Source"
    quality_max: str | None = None
    codec_preference: tuple[str, ...] = ("avc1", "hevc", "av01")
    audio_only: bool = False
    part_padding: int = 0


#: Selection and naming defaults: the highest stream the source offers with the preferred
#: codec first, and simple ``[P2]`` names. Deliberately carries no delivery decision
#: (``auto_preview`` is ``None``), because a bot's upload choice is not a default; state
#: it explicitly before calling :func:`matcha.deliver.decide`.
SELECTION_DEFAULT = Policy()


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
    """Why one engine failed. The engine id and version live on :class:`Attempt`."""

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
