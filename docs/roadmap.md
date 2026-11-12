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
