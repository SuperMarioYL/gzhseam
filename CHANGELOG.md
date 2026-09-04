# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] — 2026-09-04

### Fixed

- **Stop `_FONT_FAMILY_RE` from remapping `font-family` text inside quoted CSS
  values** (`gzhseam/fonts.py`). The font-family regex matched `font-family:`
  *anywhere* in the style string, including inside a quoted CSS `content` value
  such as `content: "font-family: bar"`. When such an in-quote font-family
  co-occurred with a real font-family remap on the same element, `[^;]+` ate the
  content value's closing quote and the replacement dropped it — leaving the
  content string unclosed and swallowing every subsequent declaration into it,
  so the whole inline style was structurally broken (not merely one font name
  rewritten). The regex is now anchored to a CSS declaration boundary
  (start-of-string or after a `;`), so only real `font-family` declarations are
  remapped; quoted content strings and every adjacent declaration survive
  verbatim. The v0.2.0 data-URL fix is not regressed, and font-stage idempotency
  is preserved.

### Maintenance

- Added a version-lockstep regression test (`tests/test_version.py`) asserting
  `VERSION == __version__ == pyproject.toml version == gzhseam --version`, so a
  future release that bumps one surface and forgets another fails CI instead of
  shipping a silent drift. (`web/site.json` carries no `content_version` field,
  so it is not part of the lockstep.)

## [0.5.0] — 2026-08-25

### Fixed

- `wash()` now honors `GzhCtx.whitelisted_tags` / `allowed_attrs` /
  `allowed_fonts` per-call config overrides instead of silently swallowing them.
  The overrides are threaded through `whitelist.filter_html` and
  `fonts.normalize_fonts` via backward-compatible optional params defaulting to
  the module-level constants.

## [0.4.0]

### Fixed

- `_serialize_fragment` no longer leaks the `<html><head></head></html>` wrapper
  when lxml creates no `<body>` (head-only decks now wash to an empty fragment).
- `gzhseam wash` on empty / whitespace-only input now fails cleanly (red `✗` +
  exit 2, no output file) instead of writing a 0-byte file with a green `✓`.

## [0.3.0]

### Fixed

- Create the output parent dir (or fail cleanly) before `write_text`, so
  `-o subdir/out.html` with a missing parent no longer tracebacks mid-run.
- Catch `UnicodeDecodeError` on the UTF-8 deck read and print a clean red
  error + exit 2 instead of a cryptic traceback on non-UTF-8 input.
- `gzhseam init` / `auth login` stubs now fail with a clean red `✗` + exit 2
  instead of a bare `NotImplementedError` traceback.

## [0.2.0]

### Fixed

- Guard `_drop_disallowed_tags` against decomposed/detached tags so
  `noscript`/`video`/`template`/`form` children no longer crash `gzhseam wash`
  with a `ValueError`.
- `normalize_style` now touches only `font-family` declarations and leaves the
  rest verbatim, so `;`-bearing values (data-URL backgrounds) survive a
  co-occurring font-family remap.

### Added

- `gzhseam feedback` subcommand (stdlib `webbrowser`, no new dep) +
  `.github/ISSUE_TEMPLATE/*.md` prefilled templates to convert cloners into
  issue filers.

## [0.1.0] — 2026-07-24

### Added

- Initial release: the GzhWash pipeline (m1, local-only) — tag-whitelist
  filter + font-constraint normalize → 公众号-editor-pasteable, in-place-editable
  HTML. CLI `gzhseam wash deck.html -o out.html`, bilingual README, demo cast.
