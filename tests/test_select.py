from __future__ import annotations

import pytest

from matcha import DEFAULT_POLICY, ApiError, Policy, Stream, bilibili
from matcha.select import codec_family, max_height, select_audio, select_video

STREAMS = (
    Stream(
        url="avc-1080",
        codec="avc1.640028",
        bandwidth=2_000_000,
        width=1920,
        height=1080,
        quality_id=80,
    ),
    Stream(
        url="avc-480",
        codec="avc1.64001F",
        bandwidth=191_380,
        width=852,
        height=480,
        quality_id=32,
    ),
    Stream(
        url="hevc-1080",
        codec="hev1.1.6.L120.90",
        bandwidth=1_500_000,
        width=1920,
        height=1080,
        quality_id=80,
    ),
    Stream(
        url="av1-480",
        codec="av01.0.08M.08",
        bandwidth=300_000,
        width=852,
        height=480,
        quality_id=32,
    ),
)

AUDIO = (
    Stream(url="aac-64", codec="mp4a.40.2", bandwidth=64_000, quality_id=30216),
    Stream(url="aac-192", codec="mp4a.40.2", bandwidth=192_000, quality_id=30280),
)


def test_quality_labels_resolve_to_heights():
    assert max_height(None) is None
    assert max_height("480p") == 480
    assert max_height("1080P") == 1080
    assert max_height("1080p60") == 1080
    assert max_height("4K") == 2160
    assert max_height("2160p") == 2160
    assert max_height("8k") == 4320
    with pytest.raises(ValueError):
        max_height("best")


def test_codec_families_accept_the_strings_sources_publish():
    assert codec_family("avc1.640032") == "avc1"
    assert codec_family("avc3.640032") == "avc1"
    assert codec_family("hev1.1.6.L120.90") == "hevc"
    assert codec_family("hvc1.1.6.L120.90") == "hevc"
    assert codec_family("av01.0.08M.08") == "av01"
    assert codec_family("mp4a.40.2") == "mp4a"
    assert codec_family(None) is None


def test_default_policy_keeps_the_old_avc_first_choice():
    chosen = select_video(STREAMS, DEFAULT_POLICY)
    assert chosen is not None and chosen.url == "avc-1080"


def test_quality_max_caps_before_quality():
    chosen = select_video(STREAMS, Policy(auto_preview=True, quality_max="480p"))
    assert chosen is not None and chosen.url == "avc-480"


def test_codec_preference_beats_height():
    chosen = select_video(STREAMS, Policy(auto_preview=True, codec_preference=("hevc",)))
    assert chosen is not None and chosen.url == "hevc-1080"


def test_codec_preference_and_cap_compose():
    policy = Policy(auto_preview=True, quality_max="480p", codec_preference=("av01",))
    chosen = select_video(STREAMS, policy)
    assert chosen is not None and chosen.url == "av1-480"


def test_unknown_codec_ranks_last_but_is_still_eligible():
    unknown = Stream(url="mystery", codec="vp09.00.10.08", bandwidth=9_000_000, height=480)
    chosen = select_video((*STREAMS, unknown), Policy(auto_preview=True, quality_max="480p"))
    assert chosen is not None and chosen.url == "avc-480"


def test_without_avc_the_next_preference_wins_even_at_lower_height():
    """The fallback order is hevc, then av01, then an unlisted codec -- pinned."""
    hevc_480 = Stream(
        url="hevc-480",
        codec="hev1.1.6.L120.90",
        bandwidth=300_000,
        width=852,
        height=480,
        quality_id=32,
    )
    av1_1080 = Stream(
        url="av1-1080",
        codec="av01.0.08M.08",
        bandwidth=2_000_000,
        width=1920,
        height=1080,
        quality_id=80,
    )
    chosen = select_video((av1_1080, hevc_480), DEFAULT_POLICY)
    assert chosen is not None and chosen.url == "hevc-480"


def test_without_a_preferred_codec_av1_beats_an_unlisted_codec():
    av1 = Stream(url="av1", codec="av01.0.08M.08", bandwidth=1_000_000, height=1080)
    unlisted = Stream(url="vp9", codec="vp09.00.10.08", bandwidth=2_000_000, height=1080)
    chosen = select_video((unlisted, av1), DEFAULT_POLICY)
    assert chosen is not None and chosen.url == "av1"


def test_empty_codec_preference_falls_back_to_quality():
    chosen = select_video(STREAMS, Policy(auto_preview=True, codec_preference=()))
    assert chosen is not None and chosen.url == "avc-1080"


def test_stream_without_a_published_height_is_eligible_under_a_cap():
    hidden = Stream(url="hidden", codec="avc1.64001F", bandwidth=1, quality_id=32)
    chosen = select_video((hidden,), Policy(auto_preview=True, quality_max="480p"))
    assert chosen is not None and chosen.url == "hidden"


def test_a_cap_that_excludes_everything_returns_none():
    chosen = select_video(STREAMS, Policy(auto_preview=True, quality_max="144p"))
    assert chosen is None


def test_audio_only_chooses_no_video():
    assert select_video(STREAMS, Policy(auto_preview=True, audio_only=True)) is None


def test_audio_picks_the_highest_bandwidth():
    chosen = select_audio(AUDIO, DEFAULT_POLICY)
    assert chosen is not None and chosen.url == "aac-192"
    assert select_audio((), DEFAULT_POLICY) is None


PLAYURL = {
    "code": 0,
    "data": {
        "quality": 80,
        "dash": {
            "duration": 100,
            "video": [
                {
                    "id": 80,
                    "bandwidth": 2_000_000,
                    "codecs": "avc1.640028",
                    "baseUrl": "https://v/avc-1080",
                    "width": 1920,
                    "height": 1080,
                },
                {
                    "id": 32,
                    "bandwidth": 191_380,
                    "codecs": "avc1.64001F",
                    "baseUrl": "https://v/avc-480",
                    "width": 852,
                    "height": 480,
                },
                {
                    "id": 80,
                    "bandwidth": 1_500_000,
                    "codecs": "hev1.1.6.L120.90",
                    "baseUrl": "https://v/hevc-1080",
                    "width": 1920,
                    "height": 1080,
                },
            ],
            "audio": [{"id": 30280, "bandwidth": 192_000, "baseUrl": "https://a/192"}],
        },
    },
}


def test_parse_playurl_takes_the_policy():
    capped = bilibili.parse_playurl(PLAYURL, policy=Policy(auto_preview=True, quality_max="480p"))
    assert capped.video is not None and capped.video.url == "https://v/avc-480"
    assert capped.quality == "480p"

    hevc = bilibili.parse_playurl(
        PLAYURL, policy=Policy(auto_preview=True, codec_preference=("hevc",))
    )
    assert hevc.video is not None and hevc.video.url == "https://v/hevc-1080"


def test_parse_playurl_default_still_prefers_avc():
    plan = bilibili.parse_playurl(PLAYURL)
    assert plan.video is not None and plan.video.url == "https://v/avc-1080"
    assert plan.quality == "1080p"
    assert plan.needs_merge


def test_parse_playurl_audio_only_prices_only_audio():
    plan = bilibili.parse_playurl(PLAYURL, policy=Policy(auto_preview=True, audio_only=True))
    assert plan.video is None
    assert plan.audio is not None and plan.audio.url == "https://a/192"
    assert plan.needs_merge is False
    assert plan.quality == "audio"
    assert plan.estimated_bytes == int(192_000 * 100 / 8)


def test_parse_playurl_reports_an_impossible_cap():
    with pytest.raises(ApiError):
        bilibili.parse_playurl(PLAYURL, policy=Policy(auto_preview=True, quality_max="144p"))


def test_unknown_hdr_quality_id_falls_back_to_the_body_quality():
    """125/126/130 are HDR/Dolby renditions of a quality the table does know."""
    body = {
        "code": 0,
        "data": {
            "quality": 120,
            "dash": {
                "duration": 10,
                "video": [
                    {
                        "id": 125,
                        "bandwidth": 3_000_000,
                        "codecs": "hev1.1.6.L150.90",
                        "baseUrl": "https://v/hdr",
                        "width": 3840,
                        "height": 2160,
                    }
                ],
                "audio": [{"id": 30280, "bandwidth": 192_000, "baseUrl": "https://a"}],
            },
        },
    }
    plan = bilibili.parse_playurl(body)
    assert plan.quality == "4K"


def test_unknown_quality_on_both_sides_still_reports_pixels():
    body = {
        "code": 0,
        "data": {
            "quality": 125,
            "dash": {
                "duration": 10,
                "video": [
                    {
                        "id": 125,
                        "bandwidth": 3_000_000,
                        "baseUrl": "https://v/hdr",
                        "width": 3840,
                        "height": 2160,
                    }
                ],
                "audio": [{"id": 30280, "bandwidth": 192_000, "baseUrl": "https://a"}],
            },
        },
    }
    plan = bilibili.parse_playurl(body)
    assert plan.quality == "3840x2160"


def test_playurl_with_only_codec_ids_still_honours_avc_first():
    body = {
        "code": 0,
        "data": {
            "quality": 32,
            "dash": {
                "duration": 10,
                "video": [
                    {
                        "id": 32,
                        "codecid": 7,
                        "bandwidth": 191_380,
                        "baseUrl": "https://v/avc",
                        "width": 852,
                        "height": 480,
                    },
                    {
                        "id": 32,
                        "codecid": 12,
                        "bandwidth": 300_000,
                        "baseUrl": "https://v/av1",
                        "width": 852,
                        "height": 480,
                    },
                ],
                "audio": [{"id": 30280, "bandwidth": 192_000, "baseUrl": "https://a"}],
            },
        },
    }
    plan = bilibili.parse_playurl(body)
    assert plan.video is not None and plan.video.url == "https://v/avc"
