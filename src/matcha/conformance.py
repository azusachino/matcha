"""Paste shapes both bots must agree on.

Daphne and suzuran import this table in their own test suites. If a bot's intake
disagrees with it, its tests fail -- which is how "the same link behaves differently in
the two bots" gets caught before a user notices it.
"""

from __future__ import annotations

from .link import canonical_url, parse

BV = "BV1aMEj62EdA"
#: paste, platform, kind, work_id, part, start, canonical. An unclaimed paste leaves the
#: platform fields empty, and the row still has to fit this shape.
Case = tuple[str, str | None, str | None, str | None, int | None, int | None, str]
# (paste, expected platform, kind, work_id, part, start, canonical)
CASES: tuple[Case, ...] = (
    (
        f"https://www.bilibili.com/video/{BV}",
        "bilibili",
        "video",
        BV,
        None,
        None,
        f"https://www.bilibili.com/video/{BV}",
    ),
    (
        f"https://www.bilibili.com/video/{BV}/?spm_id_from=333.1007&vd_source=abc&share_source=copy_web",
        "bilibili",
        "video",
        BV,
        None,
        None,
        f"https://www.bilibili.com/video/{BV}",
    ),
    (
        f"https://m.bilibili.com/video/{BV}?p=2&vd_source=abc",
        "bilibili",
        "part",
        BV,
        2,
        None,
        f"https://www.bilibili.com/video/{BV}?p=2",
    ),
    (
        f"https://www.bilibili.com/video/{BV}?p=1",
        "bilibili",
        "video",
        BV,
        None,
        None,
        f"https://www.bilibili.com/video/{BV}",
    ),
    (
        "b23.tv/BV1aMEj62EdA",
        "bilibili",
        "video",
        BV,
        None,
        None,
        f"https://www.bilibili.com/video/{BV}",
    ),
    (
        "b23.tv/BV1aMEj62EdA?p=2&vd_source=abc",
        "bilibili",
        "part",
        BV,
        2,
        None,
        f"https://www.bilibili.com/video/{BV}?p=2",
    ),
    (
        "https://bilibili.com/video/av170001",
        "bilibili",
        "video",
        "av170001",
        None,
        None,
        "https://www.bilibili.com/video/av170001",
    ),
    (
        "https://www.bilibili.com/bangumi/play/ep38979504395",
        "bilibili",
        "episode",
        "ep38979504395",
        None,
        None,
        "https://www.bilibili.com/bangumi/play/ep38979504395",
    ),
    (
        "https://www.bilibili.com/bangumi/play/ep38979504395?p=2&vd_source=abc",
        "bilibili",
        "episode",
        "ep38979504395",
        2,
        None,
        "https://www.bilibili.com/bangumi/play/ep38979504395?p=2",
    ),
    (
        f"https://www.bilibili.com/video/{BV}，",
        "bilibili",
        "video",
        BV,
        None,
        None,
        f"https://www.bilibili.com/video/{BV}",
    ),
    (
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&si=tracking&pp=xyz",
        "youtube",
        "video",
        "dQw4w9WgXcQ",
        None,
        None,
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ),
    (
        "https://youtu.be/dQw4w9WgXcQ?t=42&si=abc",
        "youtube",
        "video",
        "dQw4w9WgXcQ",
        None,
        42,
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42",
    ),
    (
        "https://www.tiktok.com/@someone/video/7300000000000000000?_r=1&_t=tracking",
        None,
        None,
        None,
        None,
        None,
        "https://www.tiktok.com/@someone/video/7300000000000000000",
    ),
)


def check() -> list[str]:
    """Return a human-readable problem per failing case (empty means conformant)."""
    from .link import strip_tracking

    problems: list[str] = []
    for paste, platform, kind, work_id, part, start, expected in CASES:
        if platform is None:
            actual = strip_tracking(paste)
            if actual != expected:
                problems.append(f"{paste!r} -> {actual!r}, expected {expected!r}")
            continue
        ref = parse(paste)
        if ref is None:
            problems.append(f"{paste!r} did not parse")
            continue
        observed = (ref.platform, ref.kind, ref.work_id, ref.part, ref.start)
        declared = (platform, kind, work_id, part, start)
        if observed != declared:
            problems.append(f"{paste!r} -> {observed}, expected {declared}")
            continue
        produced = canonical_url(ref)
        if produced != expected:
            problems.append(f"{paste!r} canonical {produced!r}, expected {expected!r}")
    return problems
