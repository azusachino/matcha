from __future__ import annotations

import pytest

from matcha import MediaInfo, Request, Session, StreamPlan, Track, TrackKind, bilibili, parse

BV = "BV1aMEj62EdA"

VIEW_WITH_SUBTITLES = {
    "code": 0,
    "data": {
        "title": "Episode",
        "subtitle": [
            {
                "lan": "zh-CN",
                "lan_doc": "中文",
                "subtitle_url": "//aisubtitle.hdslb.com/bfs/ai_subtitle/1.json",
                "format": "json",
            },
            {
                "lan": "ai-zh",
                "subtitle_url": "https://aisubtitle.hdslb.com/bfs/ai_subtitle/2.json",
            },
            "not-a-dict",
            {"lan": "en", "subtitle_url": "ftp://example/ignored.json"},
            {"lan": "ja", "subtitle_url": "https://example/subtitle.srt", "format": "srt"},
        ],
    },
}

PLAYURL_WITH_SUBTITLES = {
    "code": 0,
    "data": {
        "quality": 32,
        "subtitle": {
            "subtitles": [
                {"lan": "zh-CN", "subtitle_url": "https://example/1.json", "format": "json"}
            ]
        },
        "dash": {
            "duration": 10,
            "video": [
                {
                    "id": 32,
                    "bandwidth": 191_380,
                    "codecs": "avc1.64001F",
                    "baseUrl": "https://v/32",
                    "width": 852,
                    "height": 480,
                }
            ],
            "audio": [{"id": 30280, "bandwidth": 192_000, "baseUrl": "https://a/1"}],
        },
    },
}


def test_track_defaults_and_stream_plan_defaults():
    track = Track("https://example/subtitle.json")
    assert (track.lang, track.format, track.kind) == (None, None, TrackKind.SUBTITLE)
    plan = StreamPlan(video=None, audio=None, estimated_bytes=0, quality="", needs_merge=False)
    assert plan.tracks == ()
    assert MediaInfo("bilibili", "video", BV, "t").tracks == ()


def test_parse_view_reads_a_bangumi_subtitle_list():
    ref = parse(f"https://www.bilibili.com/video/{BV}")
    assert ref is not None
    info = bilibili.parse_view(VIEW_WITH_SUBTITLES, ref)
    assert [t.lang for t in info.tracks] == ["zh-CN", "ai-zh", "ja"]
    assert [t.format for t in info.tracks] == ["json", "json", "srt"]
    assert info.tracks[0].url == "https://aisubtitle.hdslb.com/bfs/ai_subtitle/1.json"
    assert all(t.kind is TrackKind.SUBTITLE for t in info.tracks)


def test_parse_view_keeps_absent_subtitles_absent():
    ref = parse(f"https://www.bilibili.com/video/{BV}")
    assert ref is not None
    info = bilibili.parse_view({"code": 0, "data": {"title": "t"}}, ref)
    assert info.tracks == ()


def test_parse_playurl_reads_subtitles_from_its_own_body():
    plan = bilibili.parse_playurl(PLAYURL_WITH_SUBTITLES)
    assert len(plan.tracks) == 1
    assert plan.tracks[0].kind is TrackKind.SUBTITLE
    assert plan.tracks[0].url == "https://example/1.json"


def test_parse_playurl_merges_caller_tracks_without_duplicates():
    ref = parse(f"https://www.bilibili.com/video/{BV}")
    assert ref is not None
    danmaku = bilibili.danmaku_track(38979504395)
    duplicate_subtitle = Track("https://example/1.json", "zh-CN", "json", TrackKind.SUBTITLE)
    plan = bilibili.parse_playurl(PLAYURL_WITH_SUBTITLES, tracks=(danmaku, duplicate_subtitle))
    assert [t.kind for t in plan.tracks] == [TrackKind.SUBTITLE, TrackKind.DANMAKU]
    assert plan.tracks[1].url.endswith("/x/v1/dm/list.so?oid=38979504395")


def test_danmaku_track_xml_and_protobuf_forms():
    whole = bilibili.danmaku_track(38979504395)
    assert whole.url == "https://api.bilibili.com/x/v1/dm/list.so?oid=38979504395"
    assert whole.format == "xml" and whole.kind is TrackKind.DANMAKU and whole.lang is None

    segment = bilibili.danmaku_track(38979504395, aid=170001, segment=1)
    assert segment.format == "protobuf"
    assert "/x/v2/dm/web/seg.so?" in segment.url
    assert "pid=170001" in segment.url and "segment_index=1" in segment.url

    with pytest.raises(ValueError):
        bilibili.danmaku_track(1, segment=1)
    with pytest.raises(ValueError):
        bilibili.danmaku_track(1, aid=2, segment=0)


def test_danmaku_request_carries_headers_and_cookies():
    ref = parse(f"https://www.bilibili.com/video/{BV}")
    assert ref is not None
    request = bilibili.danmaku_request(ref, Session({"SESSDATA": "secret"}), cid=38979504395)
    assert isinstance(request, Request)
    assert request.url == "https://api.bilibili.com/x/v1/dm/list.so?oid=38979504395"
    assert request.cookies == {"SESSDATA": "secret"}
    assert request.headers["Referer"] == "https://www.bilibili.com/"

    youtube = parse("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert youtube is not None
    with pytest.raises(ValueError):
        bilibili.danmaku_request(youtube, Session(), cid=1)


def test_subtitle_request_carries_the_player_headers():
    track = Track("https://example/1.json", "zh-CN", "json")
    request = bilibili.subtitle_request(track, Session({"SESSDATA": "secret"}))
    assert request.url == "https://example/1.json"
    assert request.cookies == {"SESSDATA": "secret"}
    assert request.headers["Origin"] == "https://www.bilibili.com"
    with pytest.raises(ValueError):
        bilibili.subtitle_request(bilibili.danmaku_track(1), Session())
