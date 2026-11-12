# matcha

The link-to-media pipeline shared by two Telegram bots, [`daphne`](../daphne) and
[`suzuran`](../suzuran). Pure by construction: no HTTP client, no bot framework, no
filesystem, so one implementation serves an async aiogram bot and a synchronous one.

Why it exists: the same pasted Bilibili link behaved differently in the two bots. Daphne
lost the part selection and reported a public creator as "Unknown"; suzuran printed the
paste -- `spm_id_from`, `vd_source` and all -- into its caption, its card, its NFO file
and yt-dlp's argv. Both were the same missing abstraction: nothing owned the question
"which URL may be printed".

## Modules

| Module | Owns | Leaves to the bot |
| --- | --- | --- |
| `link` | `WorkRef`, parsing, the single `canonical_url` producer | nothing |
| `platforms/bilibili` | request descriptions (`view`, `playurl`, visitor cookies), payload parsers | performing requests, cookie storage |
| `platforms/youtube` | identity only | fetching (yt-dlp) |
| `chain` | ordered engines, completeness check, attempt log | the engines themselves |
| `deliver` | upload-vs-card decision over policy and capabilities | sinks: upload, card, NFO, note capture |
| `conformance` | paste shapes both bots must agree on | running it in each repo's tests |

## The invariants

1. One producer. A printable URL comes from `canonical_url(ref)`; nothing else.
2. Round trip. `parse(canonical_url(parse(paste))) == parse(paste)`.
3. Capability is not policy. `Policy.auto_preview` decides, never "we happen to know a size".
4. Absence is not a value. `None` means the source omitted it; renderers omit the field.
5. Provenance is not persisted. The pasted text is parsed once and dropped.
6. One intake normaliser: share-sheet punctuation, scheme, mobile hosts, short links.

## Two policies, one pipeline

```python
daphne  = Policy(auto_preview=True,  show_source_link=True)
suzuran = Policy(auto_preview=False, redact_personal=True, show_source_link=False, store_metadata=True)
```

Suzuran's privacy is a policy value plus its own sinks, not a fork of the workflow.

## Adding a platform

Add `src/matcha/platforms/<name>.py` exposing a `SPEC = PlatformSpec(...)` with
`parse(host, path, params)` and `canonical(ref)`, then register it in
`platforms/__init__.py`. `link`, `chain` and `deliver` stay untouched.

## Gates

```bash
make check    # ruff format --check, ruff check, pytest
```
