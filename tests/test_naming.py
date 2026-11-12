from __future__ import annotations

import pytest

from matcha import SELECTION_DEFAULT, MediaInfo, Policy, WorkRef
from matcha.naming import MAX_STEM_BYTES, extension_for, filename_for, slugify

BV = "BV1aMEj62EdA"


def info(title: str = "Best Friend", kind: str = "video", work_id: str = BV) -> MediaInfo:
    return MediaInfo("bilibili", kind, work_id, title)


def test_slugify_keeps_unicode_and_replaces_only_forbidden_characters():
    assert slugify("Best Friend") == "Best Friend"
    assert slugify("🐱躲在超市后门哈气的二人🐱") == "🐱躲在超市后门哈气的二人🐱"
    assert slugify('a/b:c*d?"e\\f|g<h>i') == "a b c d e f g h i"
    assert slugify("  spaced\t\ntitle  ") == "spaced title"
    assert slugify("trailing. . ") == "trailing"
    assert slugify("\x00\x1f") == ""


def test_default_name_is_title_plus_the_platform_extension():
    ref = WorkRef("bilibili", "video", BV)
    assert filename_for(ref, info()) == "Best Friend.mp4"


def test_part_two_is_marked_and_part_one_is_not():
    part_two = WorkRef("bilibili", "part", BV, 2)
    part_one = WorkRef("bilibili", "part", BV, 1)
    assert filename_for(part_two, info()) == "Best Friend [P2].mp4"
    assert filename_for(part_one, info()) == "Best Friend.mp4"
    # Part 1 and "no part" are the same video, so they name the same file.
    assert filename_for(WorkRef("bilibili", "video", BV), info()) == filename_for(part_one, info())


def test_part_padding_is_a_policy_value():
    ref = WorkRef("bilibili", "part", BV, 2)
    assert filename_for(ref, info(), Policy(auto_preview=False, part_padding=2)) == (
        "Best Friend [P02].mp4"
    )
    assert filename_for(ref, info(), Policy(auto_preview=False, part_padding=3)) == (
        "Best Friend [P002].mp4"
    )
    with pytest.raises(ValueError):
        filename_for(ref, info(), Policy(auto_preview=False, part_padding=-1))


def test_episode_and_collection_carry_their_work_marker():
    episode = WorkRef("bilibili", "episode", "ep38979504395")
    collection = WorkRef("bilibili", "collection", "ss12345")
    assert filename_for(episode, info(kind="episode", work_id="ep38979504395")) == (
        "Best Friend [EP38979504395].mp4"
    )
    assert filename_for(collection, info(kind="collection", work_id="ss12345")) == (
        "Best Friend [SS12345].mp4"
    )


def test_audio_only_and_content_type_drive_the_extension():
    ref = WorkRef("bilibili", "video", BV)
    assert filename_for(ref, info(), Policy(auto_preview=False, audio_only=True)) == (
        "Best Friend.m4a"
    )
    assert filename_for(ref, info(), content_type="video/webm") == "Best Friend.webm"
    assert filename_for(ref, info(), content_type="audio/mp4; codecs=mp4a") == "Best Friend.m4a"
    # An unknown content type falls back to the platform's download shape.
    assert filename_for(ref, info(), content_type="video/x-vendor") == "Best Friend.mp4"


def test_extension_for_platform_defaults():
    assert extension_for(platform="bilibili") == "mp4"
    assert extension_for(platform="youtube") == "mp4"
    assert extension_for(platform="youtube", audio_only=True) == "m4a"
    assert extension_for(platform="unknown") == "mp4"
    assert extension_for("text/vtt") == "vtt"


def test_reserved_and_awkward_names_stay_creatable():
    ref = WorkRef("bilibili", "video", BV)
    assert filename_for(ref, info("con")) == "_con.mp4"
    assert filename_for(ref, info("Title. ")) == "Title.mp4"


def test_reserved_names_apply_before_the_first_dot():
    ref = WorkRef("bilibili", "video", BV)
    assert filename_for(ref, info("CON.txt")) == "_CON.txt.mp4"
    assert filename_for(ref, info("aux.2024")) == "_aux.2024.mp4"
    # A dotted name that is not reserved is left alone.
    assert filename_for(ref, info("final.v2")) == "final.v2.mp4"


def test_a_long_title_is_truncated_by_bytes_not_characters():
    ref = WorkRef("bilibili", "video", BV)
    name = filename_for(ref, info("猫" * 300))
    assert name.endswith(".mp4")
    stem = name.removesuffix(".mp4")
    assert len(stem.encode("utf-8")) <= MAX_STEM_BYTES
    assert "猫" in stem  # decoding did not split a character


def test_markers_survive_truncation():
    ref = WorkRef("bilibili", "part", BV, 12)
    name = filename_for(ref, info("猫" * 300))
    assert name.endswith(" [P12].mp4")
    assert len(name.removesuffix(" [P12].mp4").encode("utf-8")) <= MAX_STEM_BYTES


def test_naming_is_deterministic_and_contains_no_path_separator():
    ref = WorkRef("bilibili", "part", BV, 2)
    first = filename_for(ref, info("A/B"))
    second = filename_for(ref, info("A/B"))
    assert first == second == "A B [P2].mp4"
    assert "/" not in first and "\\" not in first


def test_an_empty_title_falls_back_to_the_work_id():
    ref = WorkRef("bilibili", "video", BV)
    assert filename_for(ref, info("")) == f"{BV}.mp4"


def test_selection_default_names_simply():
    """Naming reads ``part_padding`` and nothing from the delivery half of the policy."""
    assert SELECTION_DEFAULT.part_padding == 0
    assert SELECTION_DEFAULT.auto_preview is None
    ref = WorkRef("bilibili", "part", BV, 12)
    assert filename_for(ref, info("t"), SELECTION_DEFAULT) == "t [P12].mp4"
