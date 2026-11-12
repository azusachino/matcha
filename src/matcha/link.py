"""One way in: a pasted string becomes a WorkRef, and only ``canonical_url`` prints.

The parser is deliberately tolerant (share-sheet punctuation, missing scheme, mobile
hosts) and the canonicaliser is deliberately strict (one host, one path, whitelisted
parameters). Tolerance at the edge, one form in the middle, is what stops tracking
parameters and stale part selections from reaching captions and downloaders.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlsplit, urlunsplit

from .errors import NeedsExpansionError
from .platforms import find, spec_for
from .types import WorkRef

TRAILING_PUNCTUATION = ".,;:!?)]}>\"'`，。；：！？）】》、」』"
LEADING_PUNCTUATION = "<([{\"'`（【《、「『"


def normalize_text(text: str) -> str:
    """Trim share-sheet punctuation and give a bare host a scheme."""
    cleaned = text.strip().strip(LEADING_PUNCTUATION).rstrip(TRAILING_PUNCTUATION).strip()
    return cleaned if "://" in cleaned else f"https://{cleaned}"


def parse(text: str) -> WorkRef | None:
    """Parse a pasted link, or ``None`` when no registered platform claims it.

    ``None`` means "no opinion", never "print the raw text": the caller keeps its
    generic path and still canonicalises via :func:`strip_tracking`.
    """
    try:
        parts = urlsplit(normalize_text(text))
    except ValueError:
        return None
    host = (parts.hostname or "").lower()
    spec = find(host)
    if spec is None:
        return None
    return spec.parse(host, parts.path, parse_qsl(parts.query, keep_blank_values=True))


def canonical_url(ref: WorkRef) -> str:
    """The only URL a bot may print or hand to a downloader.

    ``parse(canonical_url(parse(paste))) == parse(paste)`` holds for every paste that
    parses; only an unexpanded short link raises :class:`NeedsExpansionError`.
    """
    spec = spec_for(ref.platform)
    canonical = None if spec is None else spec.canonical(ref)
    if canonical is None:
        raise ValueError(f"no canonical form for {ref!r}")
    return canonical


def strip_tracking(url: str) -> str:
    """Canonical form for platforms without grammar: no query, no fragment, https."""
    parts = urlsplit(normalize_text(url))
    host = (parts.hostname or "").lower()
    if not host:
        return url
    return urlunsplit(("https", host, parts.path.rstrip("/") or "/", "", ""))


def with_expanded(ref: WorkRef, target: str) -> WorkRef:
    """Replace a short-link ref with its redirect target, keeping the chosen part."""
    resolved = parse(target)
    if resolved is None:
        raise NeedsExpansionError(f"{target!r} did not expand to a supported link")
    if ref.part and not resolved.part:
        resolved = WorkRef(resolved.platform, "part", resolved.work_id, ref.part, resolved.start)
    return resolved


def cache_key(ref: WorkRef) -> str:
    """Stable per-work key: part selection included, paste shape irrelevant."""
    part = f"-p{ref.part}" if ref.part else ""
    return f"{ref.platform}-{ref.work_id}{part}"


__all__ = [
    "cache_key",
    "canonical_url",
    "normalize_text",
    "parse",
    "strip_tracking",
    "with_expanded",
]
