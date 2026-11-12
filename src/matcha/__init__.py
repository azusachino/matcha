"""matcha: the link-to-media pipeline daphne and suzuran share.

Pure by construction -- no HTTP client, no bot framework, no filesystem. A bot supplies
its own I/O, its own sinks and its own :class:`~matcha.types.Policy`; the grammar,
metadata parsing, engine chaining and delivery decision come from here.
"""

from __future__ import annotations

from .deliver import decide
from .errors import ApiError, MatchaError, NeedsExpansionError
from .link import cache_key, canonical_url, normalize_text, parse, strip_tracking, with_expanded
from .platforms import bilibili, youtube
from .types import (
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
    Unavailable,
    Upload,
    WorkRef,
)

__version__ = "0.1.0"

__all__ = [
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
    "Unavailable",
    "Upload",
    "WorkRef",
    "__version__",
    "bilibili",
    "cache_key",
    "canonical_url",
    "decide",
    "normalize_text",
    "parse",
    "strip_tracking",
    "with_expanded",
    "youtube",
]
