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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gzhseam import fonts, whitelist  # noqa: E402
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
