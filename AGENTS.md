# matcha

Pure Python library. No I/O, no bot framework, no filesystem: if a change needs a
socket or a file, it belongs in the consuming bot.

## Rules

- Consumers are `vendor/daphne` and `vendor/suzuran`. A change here is a cross-repo
  contract change: bump the version, and expect both consumers to pin the new tag.
- Both bots' test suites run `matcha.conformance.check()`. A paste shape is added here
  first, then in the bots' own assertions.
- `None` means "the source did not publish it". Never substitute a placeholder.
- `canonical_url` is the only URL producer; do not add a second one for a special case.

## Gates

`make check` (ruff format --check, ruff check, pytest) before any commit.
