from __future__ import annotations

import pytest

from matcha import (
    ApiError,
    Capabilities,
    Card,
    ChainResult,
    Failure,
    File,
    MediaInfo,
    Policy,
    Reason,
    StreamPlan,
    Upload,
    bilibili,
    canonical_url,
    conformance,
    decide,
    parse,
)
from matcha.chain import ChainFailed, Probe, is_complete, run_chain
from matcha.errors import NeedsExpansionError

BV = "BV1aMEj62EdA"


def test_conformance_table():
    assert conformance.check() == []


def test_round_trip_on_every_case():
    for paste, *_ in conformance.CASES:
        ref = parse(paste)
        if ref is None:
            continue
        assert parse(canonical_url(ref)) == ref, paste


def test_short_link_needs_expansion():
    ref = parse("https://b23.tv/dQw4w9WgXcQ")
    assert ref is not None and ref.kind == "short_link"
    with pytest.raises(NeedsExpansionError):
        canonical_url(ref)


def test_expansion_keeps_the_chosen_part():
    from matcha.link import with_expanded

    short = parse(f"https://b23.tv/{BV}?p=2&vd_source=x")
    assert short is not None and short.part == 2
    expanded = with_expanded(short, f"https://www.bilibili.com/video/{BV}?share_source=copy_web")
    assert expanded.part == 2  # share sheets carry the part on the short link
    assert canonical_url(expanded) == f"https://www.bilibili.com/video/{BV}?p=2"
    # A target that names its own part wins over the carried one.
    other = with_expanded(short, f"https://www.bilibili.com/video/{BV}?p=3")
    assert other.part == 3


def test_part_is_normalised():
    assert parse(f"https://www.bilibili.com/video/{BV}?p=1").part is None  # type: ignore[union-attr]
    assert parse(f"https://www.bilibili.com/video/{BV}?p=2").part == 2  # type: ignore[union-attr]


VIEW = {
    "code": 0,
    "data": {
        "title": "🐱躲在超市后门哈气的二人🐱",
        "duration": 218,
        "pic": "http://i2.hdslb.com/bfs/archive/25787049eaa7ba31fe.png",
        "owner": {"name": "初小晓Dawn"},
        "pages": [
            {"page": 1, "part": "上", "duration": 109, "cid": 38979504395},
            {"page": 2, "part": "（纯享版）", "duration": 109, "cid": 39558775483},
        ],
    },
}


def test_parse_view_reads_owner_parts_and_selected_duration():
    ref = parse(f"https://www.bilibili.com/video/{BV}?p=2")
    assert ref is not None
    info = bilibili.parse_view(VIEW, ref, canonical=canonical_url(ref))
    assert info.creator == "初小晓Dawn"
    assert info.duration_s == 109
    assert info.is_multi_part
    assert info.parts[1].title == "（纯享版）"
    assert info.canonical_url.endswith("?p=2")
    assert info.thumbnail_url is not None


def test_parse_view_keeps_absent_fields_absent():
    ref = parse(f"https://www.bilibili.com/video/{BV}")
    assert ref is not None
    info = bilibili.parse_view({"code": 0, "data": {"title": "t", "pages": []}}, ref)
    assert info.creator is None and info.thumbnail_url is None and info.duration_s is None


def test_parse_view_rejects_error_codes():
    with pytest.raises(ApiError):
        bilibili.parse_view(
            {"code": -404, "message": "啥都木有"}, parse("https://b23.tv/BV1aMEj62EdA")
        )


PLAYURL = {
    "code": 0,
    "data": {
        "quality": 32,
        "dash": {
            "duration": 109,
            "video": [
                {
                    "id": 32,
                    "bandwidth": 191380,
                    "codecid": 7,
                    "baseUrl": "https://v/32",
                    "width": 852,
                    "height": 480,
                },
                {
                    "id": 16,
                    "bandwidth": 85889,
                    "codecid": 7,
                    "baseUrl": "https://v/16",
                    "width": 640,
                    "height": 360,
                },
                {
                    "id": 32,
                    "bandwidth": 300000,
                    "codecid": 12,
                    "baseUrl": "https://v/av1",
                    "width": 852,
                    "height": 480,
                },
            ],
            "audio": [{"id": 30280, "bandwidth": 64000, "baseUrl": "https://a/1"}],
        },
    },
}


def test_plan_prefers_h264_and_prices_the_download():
    plan = bilibili.parse_playurl(PLAYURL)
    assert plan.video is not None and plan.video.url == "https://v/32"
    assert plan.audio is not None
    assert plan.needs_merge
    expected = int((191380 + 64000) * 109 / 8)
    assert plan.estimated_bytes == expected
    assert plan.quality == "480p"


INFO = MediaInfo("bilibili", "video", BV, "title")


def test_policy_not_capability_decides():
    plan = StreamPlan(
        video=None, audio=None, estimated_bytes=10**6, quality="480p", needs_merge=True
    )
    caps = Capabilities(max_upload_bytes=50 * 10**6)
    assert isinstance(decide(INFO, plan, caps, Policy(auto_preview=True)), Upload)
    assert decide(INFO, plan, caps, Policy(auto_preview=False)) == Card(Reason.MANUAL_POLICY)
    assert decide(INFO, None, caps, Policy(auto_preview=True)) == Card(Reason.NO_PLAN)
    big = StreamPlan(video=None, audio=None, estimated_bytes=10**9, quality="4K", needs_merge=True)
    assert decide(INFO, big, caps, Policy(auto_preview=True)) == Card(Reason.TOO_LARGE)
    blocked = Capabilities(max_upload_bytes=50 * 10**6, preview_allowed=False)
    assert decide(INFO, plan, blocked, Policy(auto_preview=True)) == Card(Reason.NO_ACCESS)


class _Engine:
    def __init__(self, id_: str, outcome, version="1.0"):
        self.id = id_
        self._outcome = outcome
        self._version = version

    def version(self) -> str:
        return self._version

    def attempt(self):
        return self._outcome


def test_chain_skips_failures_and_records_them():
    engines = [
        _Engine("viewport", Failure("viewport", "0.5.1", Reason.RATE_LIMITED, "412")),
        _Engine("native", File("/tmp/a.mp4")),
    ]
    result = run_chain(engines)
    assert isinstance(result, ChainResult)
    assert result.engine == "native"
    assert [a.engine for a in result.attempts] == ["viewport", "native"]


def test_chain_rejects_a_truncated_result():
    engines = [_Engine("native", File("/tmp/a.mp4")), _Engine("ytdlp", File("/tmp/b.mp4"))]
    probes = {"/tmp/a.mp4": Probe(900_000, 3.0), "/tmp/b.mp4": Probe(9_000_000, 108.0)}
    result = run_chain(engines, probe=probes.__getitem__, expected_duration_s=109)
    assert result.path == "/tmp/b.mp4"
    with pytest.raises(ChainFailed) as caught:
        run_chain(engines[:1], probe=probes.__getitem__, expected_duration_s=109)
    assert caught.value.reason == Reason.EXTRACTOR_FAILED


def test_completeness_thresholds():
    assert not is_complete(Probe(0), None)
    assert not is_complete(Probe(5_000_000, 10.0), 109)
    assert is_complete(Probe(5_000_000, 108.0), 109)
