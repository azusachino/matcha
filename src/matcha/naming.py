"""Deterministic, filesystem-safe names for a saved work.

Both bots used to build names themselves, so a multi-part Bilibili video could overwrite
its own first part and each bot's cache used a different convention. This module is the
one namer: same :class:`WorkRef`, :class:`MediaInfo` and :class:`Policy` produce the same
name on every machine, with no clock, random suffix or filesystem probe.

The shape follows gallery-dl's templates: a title slug, an episode marker when the work
is an episode, a part marker when a part was selected, then an extension derived from the
content type. Padding is a policy value, because a library that sorts lexicographically
wants ``P02`` while a chat cache reads better as ``P2``.
"""

from __future__ import annotations

import re
import unicodedata

from .types import DEFAULT_POLICY, MediaInfo, Policy, WorkRef

#: Characters no common filesystem accepts. They become spaces, not underscores:
#: ``"a/b"`` reads as ``"a b"``, which is what a title meant.
FORBIDDEN_CHARS = frozenset('<>:"/\\|?*')

#: Windows device names, case-insensitive. A file called ``con.mp4`` cannot be created.
RESERVED_NAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{i}" for i in range(1, 10)}
    | {f"lpt{i}" for i in range(1, 10)}
)

#: Most filesystems cap a component at 255 bytes; leave room for the extension and
#: markers while keeping CJK titles from blowing the limit.
MAX_STEM_BYTES = 180

MIME_EXTENSIONS: dict[str, str] = {
    "video/mp4": "mp4",
    "video/webm": "webm",
    "video/x-matroska": "mkv",
    "video/quicktime": "mov",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/mpeg": "mp3",
    "audio/aac": "aac",
    "audio/flac": "flac",
    "audio/ogg": "ogg",
    "audio/opus": "opus",
    "application/x-subrip": "srt",
    "text/vtt": "vtt",
    "application/json": "json",
}

#: What a platform's downloader produces when the content type is not published.
PLATFORM_EXTENSIONS: dict[str, str] = {"bilibili": "mp4", "youtube": "mp4"}
AUDIO_EXTENSION = "m4a"
FALLBACK_EXTENSION = "mp4"

_WHITESPACE_RE = re.compile(r"\s+")


def slugify(title: str) -> str:
    """A filesystem-safe stem: forbidden characters become spaces, runs collapse.

    Unicode is preserved (a Chinese title stays readable); only characters a filesystem
    would reject are replaced. Leading and trailing dots/spaces go, so the result can
    never be a hidden file or a Windows trailing-dot name.
    """
    text = unicodedata.normalize("NFC", title or "")
    cleaned = "".join(
        " " if ch in FORBIDDEN_CHARS or ord(ch) < 32 or ord(ch) == 127 else ch for ch in text
    )
    return _WHITESPACE_RE.sub(" ", cleaned).strip(" .")


def _truncate(text: str, max_bytes: int = MAX_STEM_BYTES) -> str:
    """Trim to a UTF-8 byte budget without splitting a character or leaving a dot/space."""
    if max_bytes <= 0:
        return ""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore").rstrip(" .")


def extension_for(
    content_type: str | None = None,
    *,
    platform: str = "",
    audio_only: bool = False,
) -> str:
    """Extension from a published content type, else the platform's download shape.

    A bot that already read a ``Content-Type`` passes it; one that did not gets the
    platform default (Bilibili DASH and yt-dlp both produce mp4, audio-only is m4a).
    Unknown types fall back rather than inventing an extension from a vendor string.
    """
    if content_type:
        mime = content_type.split(";", 1)[0].strip().lower()
        if mime in MIME_EXTENSIONS:
            return MIME_EXTENSIONS[mime]
    if audio_only:
        return AUDIO_EXTENSION
    return PLATFORM_EXTENSIONS.get(platform, FALLBACK_EXTENSION)


def _part_suffix(part: int, padding: int) -> str:
    if padding < 0:
        raise ValueError("part_padding must be >= 0")
    label = f"P{part:0{padding}d}" if padding else f"P{part}"
    return f" [{label}]"


def filename_for(
    ref: WorkRef,
    info: MediaInfo,
    policy: Policy = DEFAULT_POLICY,
    *,
    content_type: str | None = None,
) -> str:
    """The one name for a saved work: title, markers, extension, nothing environmental.

    Part 1 and "no part" name the same file because they are the same video; part 2 and
    later carry ``[P2]`` (or ``[P02]`` with ``Policy.part_padding``). Episodes and
    collections carry their work id marker, so a season's files never collide.
    """
    title = slugify(info.title) or slugify(ref.work_id) or "matcha"
    suffix = ""
    if ref.is_episode:
        suffix += f" [{slugify(ref.work_id).upper()}]"
    if ref.part and ref.part > 1:
        suffix += _part_suffix(ref.part, policy.part_padding)

    room = max(32, MAX_STEM_BYTES - len(suffix.encode("utf-8")))
    stem = f"{_truncate(title, room)}{suffix}".strip()
    # Windows reserves the name before the first dot: "CON.txt" is as unusable as "CON".
    if stem.split(".", 1)[0].lower() in RESERVED_NAMES:
        stem = f"_{stem}"
    extension = extension_for(content_type, platform=ref.platform, audio_only=policy.audio_only)
    return f"{stem}.{extension}"


__all__ = [
    "AUDIO_EXTENSION",
    "FALLBACK_EXTENSION",
    "FORBIDDEN_CHARS",
    "MAX_STEM_BYTES",
    "MIME_EXTENSIONS",
    "PLATFORM_EXTENSIONS",
    "RESERVED_NAMES",
    "extension_for",
    "filename_for",
    "slugify",
]
