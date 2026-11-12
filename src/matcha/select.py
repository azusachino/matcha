"""Choosing one stream set from parsed candidates, by policy.

Selection used to live inside ``platforms/bilibili.parse_playurl`` as a hardcoded
"prefer AVC, then the highest id". That made a product choice in a parser: a bot that
wanted 480p HEVC had to fork the parse. Here the parser only reports what the source
published; this module applies ``Policy.quality_max``, ``Policy.codec_preference`` and
``Policy.audio_only`` to the candidates.

The default policy reproduces the old behavior: the highest AVC stream the source
offers, then the highest-bandwidth audio. Capability plays no part -- a plan is chosen
before anyone knows whether it will be uploaded.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from .types import Policy, Stream

#: Height for each quality label Bilibili and yt-dlp use. Unknown labels fail loudly
#: rather than silently uncapping the download.
QUALITY_HEIGHTS: dict[str, int] = {
    "360p": 360,
    "480p": 480,
    "540p": 540,
    "720p": 720,
    "720p60": 720,
    "1080p": 1080,
    "1080p+": 1080,
    "1080p60": 1080,
    "1440p": 1440,
    "2160p": 2160,
    "4k": 2160,
    "8k": 4320,
}

#: Codec strings start with a family prefix: ``avc1.640032``, ``hev1.1.6.L120.90``,
#: ``av01.0.08M.08``. Preference entries may use either the family or a common alias.
CODEC_FAMILIES: dict[str, str] = {
    "avc1": "avc1",
    "avc3": "avc1",
    "h264": "avc1",
    "hev1": "hevc",
    "hvc1": "hevc",
    "h265": "hevc",
    "av01": "av01",
    "av1": "av01",
}

_HEIGHT_RE = re.compile(r"(\d{3,4})p?")


def max_height(quality_max: str | None) -> int | None:
    """Resolve ``"480p"``, ``"1080P"``, ``"4K"`` or ``"2160p"`` to a pixel height."""
    if quality_max is None:
        return None
    key = quality_max.strip().lower()
    if key in QUALITY_HEIGHTS:
        return QUALITY_HEIGHTS[key]
    match = _HEIGHT_RE.fullmatch(key)
    if match:
        return int(match.group(1))
    raise ValueError(f"quality_max {quality_max!r} is not a height like '480p'")


def codec_family(codec: str | None) -> str | None:
    """The family a codec string belongs to, or its bare prefix when unlisted."""
    if not codec:
        return None
    prefix = codec.split(".", 1)[0].strip().lower()
    return CODEC_FAMILIES.get(prefix, prefix or None)


def _preference(policy: Policy) -> tuple[str, ...]:
    return tuple(codec_family(codec) or codec.strip().lower() for codec in policy.codec_preference)


def _rank(stream: Stream, preference: tuple[str, ...]) -> int:
    family = codec_family(stream.codec)
    return preference.index(family) if family in preference else len(preference)


def select_video(streams: Sequence[Stream], policy: Policy) -> Stream | None:
    """Pick one video stream: quality cap first, then codec preference, then quality.

    Codec preference is a priority, not a tie-breaker: a preferred 480p stream beats an
    unlisted 4K one, which is what the old AVC-first pick did. When the preferred codec
    is absent the next entry wins the same way (``hevc`` before ``av01`` before an
    unlisted codec), so the fallback is never accidental. An empty
    ``codec_preference`` ranks every stream equally and lets height/bandwidth decide.

    A stream whose height the source did not publish is eligible under a cap -- absence
    is not evidence that it exceeds the cap -- but a known-height stream wins the tie.
    Returns ``None`` when the policy is audio-only or the cap excludes every candidate.
    """
    if policy.audio_only:
        return None
    cap = max_height(policy.quality_max)
    eligible = [s for s in streams if cap is None or s.height is None or s.height <= cap]
    if not eligible:
        return None
    preference = _preference(policy)
    return max(
        eligible,
        key=lambda s: (
            -_rank(s, preference),
            s.height or 0,
            s.quality_id or 0,
            s.bandwidth,
        ),
    )


def select_audio(streams: Sequence[Stream], policy: Policy) -> Stream | None:
    """Pick one audio stream: codec preference, then the highest bandwidth."""
    if not streams:
        return None
    preference = _preference(policy)
    return max(
        streams,
        key=lambda s: (-_rank(s, preference), s.bandwidth, s.quality_id or 0),
    )


__all__ = [
    "CODEC_FAMILIES",
    "QUALITY_HEIGHTS",
    "codec_family",
    "max_height",
    "select_audio",
    "select_video",
]
