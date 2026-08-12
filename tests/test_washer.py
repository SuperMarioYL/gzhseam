"""Tests for the GzhWash pipeline (:mod:`gzhseam.washer`) + font stage.

Covers the m1 contract end-to-end:

- the pipeline runs the three stages in order (whitelist → fonts → cdn)
  and returns a :class:`GzhArtifact` with the union of all diagnostics;
- font-family with no allowed member maps to the bucket default
  (sans/serif/mono) so the author's intent survives;
- font-family with one allowed member survives verbatim;
- the m2 CDN stage is wired into the pipeline and raises
  :class:`NotImplementedError` when ``upload_cdn=True`` — proving the m2
  contract is reachable without being implemented;
- the pipeline is idempotent on the m1 path.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gzhseam import fonts, whitelist  # noqa: E402
from gzhseam import cli as cli_mod  # noqa: E402
from gzhseam.washer import wash, GzhCtx, GzhArtifact  # noqa: E402


# --- font stage ------------------------------------------------------------


def test_font_family_maps_unknown_to_bucket_default():
    new, notes = fonts.normalize_style("font-family: 'Fira Code', monospace")
    assert "monospace" in new
    assert "Fira Code" not in new
    assert notes  # a rewrite was reported


def test_font_family_keeps_allowed_token_verbatim():
    new, notes = fonts.normalize_style(
        "font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif"
    )
    assert "PingFang SC" in new
    assert "Microsoft YaHei" in new
    assert "sans-serif" in new
    assert notes == []


def test_font_family_buckets_by_first_token_when_no_allowed_member():
    # 'Operator Mono' is a mono font not in the allowed set; the bucket
    # default for mono should be substituted so the code-style intent survives.
    new, _ = fonts.normalize_style("font-family: 'Operator Mono', 'Fira Code'")
    assert "Menlo" in new or "Monaco" in new or "Consolas" in new
    assert "monospace" in new


def test_font_normalize_idempotent():
    src = "<p style='font-family: \"Fira Code\", monospace'>code</p>"
    once, n1 = fonts.normalize_fonts(src)
    twice, n2 = fonts.normalize_fonts(once)
    assert once == twice
    assert n2 == []


def test_font_normalize_preserves_other_declarations():
    new, _ = fonts.normalize_style(
        "color: red; font-family: 'Fira Code'; font-size: 14px"
    )
    assert "color: red" in new
    assert "font-size: 14px" in new


def test_normalize_style_preserves_data_url_with_semicolon_in_value():
    """Regression for v0.2.0 ``fix-fonts-normalize-style-corrupts-semicolon-in-values``.

    A ``;``-bearing value (a data-URL ``background``) co-occurring with a
    non-allowed ``font-family`` remap must survive intact. The old
    implementation re-parsed the whole style with a ``;``-splitting regex and
    re-emitted every declaration, splitting the data URL at its ``;``, leaving
    ``url(`` unclosed, truncating the data URL, and dropping adjacent
    declarations. The fix touches ONLY ``font-family`` declarations and leaves
    the rest of the style string verbatim.
    """
    src = (
        "font-family: 'Fira Code', monospace; "
        "background: url(data:image/png;base64,iVBOR=) no-repeat; "
        "color: red; font-size: 14px"
    )
    new, notes = fonts.normalize_style(src)
    # the data URL survived intact (no ; -split corruption)
    assert "url(data:image/png;base64,iVBOR=) no-repeat" in new
    # no stray ;; / "; ;" artifacts from a ;-splitting re-parse
    assert ";;" not in new
    assert "; ;" not in new
    # font-family WAS remapped ('Fira Code' is not allowed -> mono bucket)
    assert "Fira Code" not in new
    assert "monospace" in new
    assert notes  # a rewrite was reported
    # adjacent declarations survived verbatim
    assert "color: red" in new
    assert "font-size: 14px" in new


# --- pipeline (m1 path) ----------------------------------------------------


def test_wash_returns_artifact_with_html_and_violations():
    src = (
        "<agent-deck>"
        "<p style='font-family: \"Fira Code\", monospace'>code</p>"
        "<script>bad()</script>"
        "</agent-deck>"
    )
    art = wash(src)
    assert isinstance(art, GzhArtifact)
    assert art.html
    assert "<script" not in art.html
    assert "<agent-deck" not in art.html
    assert "code" in art.html
    assert "Fira Code" not in art.html  # remapped
    assert art.violations
    assert art.notes


def test_wash_idempotent_on_m1_path():
    src = "<agent-deck><p style='font-family:\"Fira Code\"'>x</p></agent-deck>"
    once = wash(src)
    twice = wash(once.html)
    assert once.html == twice.html
    # second pass: whitelist is clean (the first pass already stripped it),
    # but font notes may differ — we only assert the html is stable.
    assert twice.violations == []


def test_wash_with_default_ctx_is_local_only():
    """The default GzhCtx must not flip on the m2 cdn stage."""
    ctx = GzhCtx()
    assert ctx.upload_cdn is False
    art = wash("<p>hi</p>", ctx)
    assert art.replaced_imgs == []


def test_wash_upload_cdn_true_raises_not_implemented():
    """m2 stage is wired into the pipeline but raises — the m1 ship never
    touches the network by accident."""
    with pytest.raises(NotImplementedError):
        wash("<p>hi</p>", GzhCtx(upload_cdn=True))


def test_wash_sample_deck_fixture_end_to_end():
    deck = (
        Path(__file__).parent / "fixtures" / "sample_deck.html"
    ).read_text(encoding="utf-8")
    art = wash(deck)
    # all platform-incompatible tags gone
    for needle in ("<script", "<canvas", "<iframe", "<video", "onclick", "<!--"):
        assert needle not in art.html, f"washed output still contains {needle!r}"
    # fonts normalized
    for bad_font in ("Fira Code", "Operator Mono", "Inter Tight"):
        assert bad_font not in art.html, f"font {bad_font!r} survived the wash"
    # something survived — we didn't blank the deck
    assert "Claude Code" in art.html or "claude-code" in art.html
    assert art.violations


# --- m2/m3 stubs (contract preserved) --------------------------------------


def test_cdn_replace_stub_raises():
    from gzhseam import cdn
    with pytest.raises(NotImplementedError):
        cdn.replace("<p>hi</p>")


def test_gzh_client_stub_raises():
    from gzhseam.api import gzh_client
    client = gzh_client.GzhClient(appid="x", secret="y")
    with pytest.raises(NotImplementedError):
        client.upload_image(b"")
    with pytest.raises(NotImplementedError):
        client.material_add(b"")


def test_token_cache_stub_raises():
    from gzhseam.api import auth
    cache = auth.TokenCache()
    with pytest.raises(NotImplementedError):
        cache.get()
    with pytest.raises(NotImplementedError):
        cache.put("tok", 7200)


# --- v0.3.0 CLI clean-failure regressions ------------------------------------
# All three v0.3.0 fixes share one contract: an edge-case input that used to
# abort with a bare Python traceback (exit 1, empty output) must now fail with
# the same clean red ``✗`` + ``sys.exit(2)`` pattern ``wash --cdn`` already uses
# (cli.py:99-103). The clean ``sys.exit(2)`` surfaces in CliRunner as
# ``r.exit_code == 2`` + ``r.exception`` being a ``SystemExit`` (the expected
# clean-exit mechanism) — NOT the old bad exception type (``NotImplementedError``,
# ``UnicodeDecodeError``, ``OSError``). Each case below asserts exit 2, a ``✗``
# line in output, and that the old traceback type is gone.


def test_wash_creates_missing_output_parent_dir(tmp_path):
    """v0.3.0 ``fix-wash-output-dir-not-created`` — happy path.

    ``-o subdir/out.html`` where ``subdir/`` does not exist used to abort
    mid-run with an uncaught ``FileNotFoundError`` traceback, AFTER the wash
    already succeeded and the three cyan progress lines were printed. Now the
    parent dir is created (``parents=True, exist_ok=True``) and the output file
    is written, so the single happy path completes cleanly.
    """
    deck = tmp_path / "deck.html"
    deck.write_text("<p>hi</p>", encoding="utf-8")
    out = tmp_path / "subdir" / "out.html"  # subdir/ does not exist yet
    assert not out.parent.exists()

    r = CliRunner().invoke(cli_mod.cli, ["wash", str(deck), "-o", str(out)])

    assert r.exit_code == 0, r.output
    assert r.exception is None
    assert out.exists()
    assert out.read_text(encoding="utf-8")  # non-empty output written


def test_wash_fails_cleanly_when_output_parent_is_a_file(tmp_path):
    """v0.3.0 ``fix-wash-output-dir-not-created`` — clean failure.

    When the ``-o`` parent path collides with an existing file, ``mkdir``
    raises an ``OSError`` (``FileExistsError``) which is now caught and
    reported as a clean red ``✗`` + ``sys.exit(2)`` — instead of an uncaught
    traceback mid-run after the wash already succeeded. No output file is
    written.
    """
    deck = tmp_path / "deck.html"
    deck.write_text("<p>hi</p>", encoding="utf-8")
    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir", encoding="utf-8")
    out = blocker / "out.html"  # parent is a file -> OSError on mkdir

    r = CliRunner().invoke(cli_mod.cli, ["wash", str(deck), "-o", str(out)])

    assert r.exit_code == 2, r.output
    assert "✗" in r.output
    # the OSError was caught -> only a clean SystemExit remains (no OSError
    # traceback propagated)
    assert not isinstance(r.exception, OSError)
    assert not out.exists()


def test_wash_fails_cleanly_on_non_utf8_input(tmp_path):
    """v0.3.0 ``fix-wash-non-utf8-input-traceback``.

    A deck saved as latin-1 (plausible for the CN audience gzhseam targets, and
    for any non-coding-agent HTML fed in) used to raise an uncaught
    ``UnicodeDecodeError`` traceback and exit 1 with no message. Now the UTF-8
    read is guarded and fails with a clean red ``✗`` + a "not valid UTF-8" line
    + ``sys.exit(2)`` — no output file written.
    """
    deck = tmp_path / "deck.html"
    deck.write_bytes(b"<p>caf\xe9</p>")  # 0xe9 is invalid as UTF-8
    out = tmp_path / "out.html"

    r = CliRunner().invoke(cli_mod.cli, ["wash", str(deck), "-o", str(out)])

    assert r.exit_code == 2, r.output
    assert "✗" in r.output
    assert "not valid UTF-8" in r.output
    # the UnicodeDecodeError was caught -> only a clean SystemExit remains
    assert not isinstance(r.exception, UnicodeDecodeError)
    assert not out.exists()


def test_init_stub_fails_cleanly():
    """v0.3.0 ``fix-init-auth-stub-traceback``.

    ``gzhseam init`` used to ``raise NotImplementedError`` directly, giving a
    cloner a bare Python traceback (exit 1, no console output) as their first
    CLI impression. Now it fails with the same clean red ``✗`` + ``sys.exit(2)``
    pattern ``wash --cdn`` uses — exit 2, a ``✗`` line in output, and the
    ``NotImplementedError`` is caught (no traceback propagated). The stub
    message still points at the roadmap.
    """
    r = CliRunner().invoke(cli_mod.cli, ["init"])

    assert r.exit_code == 2, r.output
    assert "✗" in r.output
    # the NotImplementedError was caught -> only a clean SystemExit remains
    assert not isinstance(r.exception, NotImplementedError)
    assert "m3 stage" in r.output  # stub message still points at the roadmap


def test_auth_login_stub_fails_cleanly():
    """v0.3.0 ``fix-init-auth-stub-traceback``.

    ``gzhseam auth login`` gets the same clean-failure treatment as
    ``gzhseam init`` above — exit 2, a ``✗`` line, the ``NotImplementedError``
    caught, and the stub message still points at the roadmap.
    """
    r = CliRunner().invoke(cli_mod.cli, ["auth", "login"])

    assert r.exit_code == 2, r.output
    assert "✗" in r.output
    assert not isinstance(r.exception, NotImplementedError)
    assert "m2 stage" in r.output  # stub message still points at the roadmap


# --- v0.4.0 CLI clean-failure regressions ------------------------------------
# The v0.3.0 clean-failure theme had one inverse gap: an empty or
# whitespace-only deck (or, after the v0.4.0 fragment fix, a head-only deck
# that washes to nothing) used to exit 0 with a green ``✓`` and a 0-byte
# output file — the "empty input" violation surfaced only under --verbose.
# Now the empty-output case fails with the same clean red ``✗`` + sys.exit(2)
# pattern the non-UTF-8 / missing-output-dir / init-auth-stub paths use, and
# writes no output file.


def test_wash_fails_cleanly_on_empty_input(tmp_path):
    """v0.4.0 ``fix-wash-silent-success-on-empty-input`` — empty file.

    ``gzhseam wash empty.html -o out.html`` used to exit 0 with a green ``✓``
    and write a 0-byte output file, surfacing the "empty input" violation
    only under ``--verbose``. Now it fails with the same clean red ``✗`` +
    ``sys.exit(2)`` pattern the non-UTF-8 / missing-output-dir / init-auth-stub
    paths use, and writes no output file. Pre-fix: exit 0, ``✓`` in output,
    0-byte ``out.html`` written.
    """
    deck = tmp_path / "deck.html"
    deck.write_text("", encoding="utf-8")  # empty
    out = tmp_path / "out.html"

    r = CliRunner().invoke(cli_mod.cli, ["wash", str(deck), "-o", str(out)])

    assert r.exit_code == 2, r.output
    assert "✗" in r.output
    assert "✓" not in r.output  # the green silent-success line is gone
    assert not out.exists()  # no 0-byte file written


def test_wash_fails_cleanly_on_whitespace_only_input(tmp_path):
    """v0.4.0 ``fix-wash-silent-success-on-empty-input`` — whitespace-only.

    Same contract as the empty-file case above, but for a deck containing only
    whitespace (spaces/tabs/newlines, no content). The pre-fix CLI wrote a
    0-byte file and printed a green ``✓``; now it fails cleanly.
    """
    deck = tmp_path / "deck.html"
    deck.write_text("   \n\t  \n", encoding="utf-8")  # whitespace-only
    out = tmp_path / "out.html"

    r = CliRunner().invoke(cli_mod.cli, ["wash", str(deck), "-o", str(out)])

    assert r.exit_code == 2, r.output
    assert "✗" in r.output
    assert "✓" not in r.output
    assert not out.exists()


def test_wash_head_only_deck_fails_cleanly_no_wrapper_leak(tmp_path):
    """v0.4.0 end-to-end composition of both fixes.

    A head-only deck (only DROP_TAGS like ``<script>``) exercises BOTH v0.4.0
    fixes in sequence:

    1. ``fix-serialize-fragment-leaks-html-head-wrapper``: the wash must NOT
       leak the ``<html><head></head></html>`` wrapper into ``artifact.html``
       — it must produce an empty fragment instead.
    2. ``fix-wash-silent-success-on-empty-input``: with the now-empty
       ``artifact.html``, the CLI must fail cleanly (red ``✗`` + exit 2, no
       output file) instead of the pre-fix path which wrote the leaked wrapper
       to the output file and printed a green ``✓``.

    Pre-fix: exit 0, ``✓`` in output, ``out.html`` written containing
    ``<html><head></head></html>``. Post-fix: exit 2, ``✗`` in output, no
    output file.
    """
    deck = tmp_path / "deck.html"
    deck.write_text("<script>alert(1)</script>", encoding="utf-8")  # head-only
    out = tmp_path / "out.html"

    r = CliRunner().invoke(cli_mod.cli, ["wash", str(deck), "-o", str(out)])

    assert r.exit_code == 2, r.output
    assert "✗" in r.output
    assert "✓" not in r.output  # no green success on the corrupted/empty output
    assert not out.exists()  # no leaked-wrapper file written
