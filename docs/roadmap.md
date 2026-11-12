# matcha roadmap

Priorities from the 2026-11-12 feature review, grounded in how the popular
repos in this space actually work: [yt-dlp]'s plugin/extractor architecture,
[gallery-dl]'s site-family base classes and filename templates, [yutto]'s
bilibili-specific track handling, the [ytdlbot] family's delivery UX, and
[aria2]'s fetcher model.

[yt-dlp]: https://github.com/yt-dlp/yt-dlp
[gallery-dl]: https://github.com/mikf/gallery-dl
[yutto]: https://github.com/yutto-dev/yutto
[ytdlbot]: https://github.com/tgbot-collection/ytdlbot
[aria2]: https://github.com/aria2/aria2

The rule that filters everything: **pure data in, data out**. If a feature
needs a socket, a file, a bot framework or a GPU, it belongs to a consuming
bot — matcha only describes, parses, selects and decides.

## Priority order

Shipped in 0.2.0: priorities 1-3 (`select.py` policy selection, `naming.py`,
and `Track` sidecars with Bilibili danmaku/subtitle request descriptions).

Shipped in 0.3.0: the v0.2.0 consumer follow-ups (issue #2) -- part cids on the
metadata, a selection default that is not a delivery decision, reserved track
vocabulary, and a type-check gate.

## 0.3.0 migration notes

- **`playurl_request` requires `cid`.** The endpoint answers -400 without one even
  for a `bvid` link, so the keyword is required and always sent; a request
  description no longer carries a blank placeholder for the caller to patch. The
  `cid` is authoritative: `page` is still sent as bookkeeping, and where a caller's
  two values disagree the endpoint serves the cid's part (measured).
  Read it from `MediaInfo.cid` instead of re-reading the `view` body, so daphne's
  cid reader and the parameter surgery in `_plan()` both go away. **Keep daphne's
  bounds check** (`"This video has N parts, not P"`) on `len(info.parts)`:
  matcha reports an out-of-range part as `cid is None`, which a caller otherwise
  reads as "the source published no cid" and turns "part 4 of 3" into a generic
  card.
- **`DEFAULT_POLICY` is now `SELECTION_DEFAULT`**, and `Policy.auto_preview` is
  `bool | None` defaulting to `None`. Selection and naming never read it, and
  `deliver.decide()` raises `PolicyError` (a `MatchaError`, so a bot's existing
  handler catches it) on an unset policy rather than reporting `MANUAL_POLICY` --
  a consumer that used the old constant for `decide()` was getting suzuran's
  product choice as its own. State `auto_preview` explicitly.
- **`PartInfo.cid` and `MediaInfo.cid` are new** and additive; both stay `None`
  when the source published no usable cid. `parse_view` also carries the body's
  own top-level `cid` (`MediaInfo.body_cid`), used only for a body that publishes
  no pages at all: that number is part 1's cid even for a `?p=2` link (measured),
  so it is never a fallback once a page exists.
- **`TrackKind.CHAPTERS`/`TrackKind.THUMBNAIL` are reserved**, listed in
  `RESERVED_TRACK_KINDS`: no parser produces them, and a cover's one home is
  `MediaInfo.thumbnail_url`. The list is documentary, not enforced -- the members
  still construct -- so check it before branching on a kind.
- **`expectation=` is typed against the caller's probe** (`Expectation[_P]`), so a
  bot's richer probe no longer only works by accident. `make check` now runs
  mypy, `py.typed` ships in the wheel so consumers see these types at all, and
  `disallow_untyped_defs` is scoped to `matcha.*` (annotating the existing test
  helpers is separate work).

## 0.2.0 migration notes

Two changes are not source-compatible for consumers pinning 0.1.0:

- **`Failure` drops `engine`/`version`.** `Attempt` already carries both, so the
  outcome no longer repeats them. Change every call site from
  `Failure(engine, version, reason, detail)` to `Failure(reason, detail)`;
  suzuran's `media_chain.py` had five at review time.
- **`deliver.decide` checks preview permission before a missing plan.** For
  `auto_preview=True` consumers the `(plan=None, preview_allowed=False)` cell
  changes from `Card(NO_PLAN)` to `Card(NO_ACCESS)` — a user-visible caption
  change in daphne. Daphne should pin that cell when it re-pins matcha.

Additive changes (`Policy` fields, `Track`, `StreamPlan.tracks`,
`MediaInfo.tracks`, `is_complete(expectation=...)`) keep their old defaults.

1. **Format policy** — replace the hardcoded AVC-first stream pick with
   `Policy` values: `quality_max`, `codec_preference`, `audio_only`.
   Selection becomes `select.py`: choose from parsed streams by policy.
   Same "policy not capability" move delivery already made; one `Policy`
   line replaces what would otherwise be a per-bot fork.
2. **Naming policy** — `filename_for(ref, info, policy)`, modeled on
   gallery-dl's filename templates. Deterministic library naming with part
   padding; kills the part-1-overwrite bug class at the core level and
   serves suzuran's library and daphne's cache from one source of truth.
3. **Sidecar tracks** — subtitles, danmaku, chapters, thumbnails as
   `Track(url, lang, format)` descriptors on `StreamPlan`. Bilibili needs
   one more request description + parser (danmaku protobuf endpoint).
   Conversion (e.g. XML/protobuf → ASS via `biliass`) stays in the bot.
   Chapters and thumbnails shipped as vocabulary only: chapters arrive inline
   in a player body (a future `Chapter` type, not a sidecar URL) and a cover's
   one home is `MediaInfo.thumbnail_url`, so both kinds are reserved
   (`RESERVED_TRACK_KINDS`) and nothing produces them.
4. **Live conformance harness** — `conformance.live(platform)`: hit one
   known-good URL per platform, assert the parse succeeds. The early
   warning system for the extractor-drift failure class that started the
   2026-11 audit; bots run it on a schedule in their CI.
5. **Platform archetypes** — site-family base specs (booru, mastodon,
   …), modeled on gallery-dl's category system, so latte (yande) and
   daphne's pixiv/bluesky land as grammar work instead of bespoke modules.
6. **Collection/playlist refs** — `WorkRef.kind` for favorites, seasons
   and channels plus pagination request descriptions; batch downloads
   like yutto's.

## Later candidates

- External fetcher engine descriptions: aria2-RPC (multi-connection,
  resume) and ffmpeg segment downloads; the bot wires the RPC, matcha
  describes the plan.
- HLS/live stream plans: segment lists with `needs_merge` variants of
  `StreamPlan` for Twitch/YouTube-live VODs.
- `Reason` vocabulary growth per platform: age-gated, cookie-required,
  PO-token-challenge.

## Explicitly out of scope

Quotas, progress bars and UI (ytdlbot's domain); cookie storage (bots
hold secrets); executing aria2/ffmpeg; format conversion (re-encodes,
GPU); any Telegram-layer concern.
