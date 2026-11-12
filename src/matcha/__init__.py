"""matcha: the link-to-media pipeline daphne and suzuran share.

Pure by construction -- no HTTP client, no bot framework, no filesystem. A bot supplies
its own I/O, its own sinks and its own :class:`~matcha.types.Policy`; the grammar,
metadata parsing, engine chaining and delivery decision come from here.
"""

from __future__ import annotations

from .deliver import decide
from .errors import ApiError, MatchaError, NeedsExpansionError
from .link import cache_key, canonical_url, normalize_text, parse, strip_tracking, with_expanded
from .naming import extension_for, filename_for, slugify
from .platforms import bilibili, youtube
from .select import codec_family, max_height, select_audio, select_video
from .types import (
    DEFAULT_POLICY,
    RESERVED_TRACK_KINDS,
    Attempt,
    Capabilities,
    Card,
    ChainResult,
    Delivery,
    Failure,
    File,
    MediaInfo,
    PartInfo,
    Policy,
    Reason,
    Request,
    Session,
    Stream,
    StreamPlan,
    Track,
    TrackKind,
    Unavailable,
    Upload,
    WorkRef,
)

__version__ = "0.2.0"

__all__ = [
    "DEFAULT_POLICY",
    "RESERVED_TRACK_KINDS",
    "ApiError",
    "Attempt",
    "Capabilities",
    "Card",
    "ChainResult",
    "Delivery",
    "Failure",
    "File",
    "MatchaError",
    "MediaInfo",
    "NeedsExpansionError",
    "PartInfo",
    "Policy",
    "Reason",
    "Request",
    "Session",
    "Stream",
    "StreamPlan",
    "Track",
    "TrackKind",
    "Unavailable",
    "Upload",
    "WorkRef",
    "__version__",
    "bilibili",
    "cache_key",
    "canonical_url",
    "codec_family",
    "decide",
    "extension_for",
    "filename_for",
    "max_height",
    "normalize_text",
    "parse",
    "select_audio",
    "select_video",
    "slugify",
    "strip_tracking",
    "with_expanded",
    "youtube",
]
