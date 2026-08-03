"""Tests for the whitelist stage (:mod:`gzhseam.whitelist`).

These pin the m1 contract:

- platform-incompatible tags (``script``, ``canvas``, ``iframe``, ...) are
  removed *with* their contents;
- non-allowlisted but non-dangerous tags (``<agent-deck>``) are *unwrapped*
  (contents lifted into the parent);
- non-allowlisted attributes (including every ``on*`` event handler) are
  stripped;
- HTML comments are removed;
- the stage is idempotent (a second pass produces zero new violations).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# allow running tests from inside the build dir without installing the package
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gzhseam import whitelist  # noqa: E402


def test_empty_input_returns_empty_with_violation():
    out, v = whitelist.filter_html("")
    assert out == ""
    assert v == ["empty input"]


def test_drops_script_with_contents():
    out, v = whitelist.filter_html(
        "<p>before</p><script>alert('x')</script><p>after</p>"
    )
    assert "<script" not in out
    assert "alert" not in out
    assert "before" in out
    assert "after" in out
    assert any("script" in s for s in v)


def test_drops_canvas_iframe_video_with_contents():
    src = (
        "<section>"
        "<canvas id='c'>fallback</canvas>"
        "<iframe src='https://x.invalid'>x</iframe>"
        "<video src='https://x.invalid/v.mp4'></video>"
        "<p>kept</p>"
        "</section>"
    )
    out, v = whitelist.filter_html(src)
    assert "kept" in out
    assert "<canvas" not in out
    assert "<iframe" not in out
    assert "<video" not in out
    assert "fallback" not in out  # dropped with the canvas
    assert sum("dropped" in s for s in v) >= 3


def test_unwraps_non_allowlisted_tags_keep_contents():
    """Custom agent tags (<agent-deck>, <footer data-agent=...>) are unwrapped,
    their visible text is lifted into the parent so the body survives."""
    out, v = whitelist.filter_html(
        "<agent-deck><p>hello</p></agent-deck>"
    )
    assert "<agent-deck" not in out
    assert "hello" in out
    assert any("unwrapped" in s for s in v)


def test_strips_on_event_handlers():
    out, v = whitelist.filter_html(
        '<div onclick="x()" onmouseover="y()">content</div>'
    )
    assert "onclick" not in out
    assert "onmouseover" not in out
    assert "content" in out
    assert any("onclick" in s for s in v)


def test_strips_non_allowlisted_attrs_on_allowed_tag():
    out, v = whitelist.filter_html('<p data-agent="x" role="banner">copy</p>')
    assert "data-agent" not in out
    assert "role" not in out
    assert "copy" in out
    assert any("data-agent" in s for s in v)


def test_keeps_allowlisted_attrs():
    out, _ = whitelist.filter_html(
        '<img src="https://x.invalid/a.png" alt="alt" width="100" style="color:red">'
    )
    assert "src=" in out
    assert "alt=" in out
    assert "width=" in out
    assert "style=" in out


def test_removes_html_comments():
    out, v = whitelist.filter_html("<p>a</p><!-- comment --><p>b</p>")
    assert "comment" not in out
    assert "<!--" not in out
    assert any("comment" in s for s in v)


def test_drops_head_meta_link_title():
    """A full HTML document scaffold (DOCTYPE/html/head/body) collapses to a
    fragment — head children (meta/link/title) are dropped entirely."""
    src = (
        "<!DOCTYPE html><html><head>"
        "<meta charset='utf-8'><title>t</title><link rel='stylesheet' href='x'>"
        "</head><body><p>body</p></body></html>"
    )
    out, v = whitelist.filter_html(src)
    assert "body" in out  # text survives
    assert "<meta" not in out
    assert "<link" not in out
    assert "<title" not in out


def test_idempotent_second_pass_zero_violations():
    src = (
        "<agent-deck><p onclick='x()'>hi</p>"
        "<script>bad()</script></agent-deck>"
    )
    once, v1 = whitelist.filter_html(src)
    twice, v2 = whitelist.filter_html(once)
    assert once == twice
    assert v2 == []


def test_drop_tag_with_children_does_not_crash():
    """Regression for v0.2.0 ``fix-whitelist-crash-on-drop-tag-with-children``.

    A DROP_TAG parent whose element children are also in the ``find_all``
    snapshot must not crash with ``ValueError: Cannot replace an element with
    its contents when that element is not part of a tree``. bs4 ``decompose()``
    on the parent recursively destroys the children (blanks ``.name``, orphans
    ``.parent``); the snapshot still references those destroyed tags, so a
    later iteration hits the ``unwrap()`` branch on a detached tag. The guard
    at the top of the loop skips already-destroyed/detached tags.

    Covers the four ordinary coding-agent HTML patterns that reproduced the
    crash: ``<noscript>``, ``<video>``, ``<template>``, ``<form>`` — each with
    element children. Asserts no exception is raised AND the wash completes
    (a string fragment is returned and a drop violation is reported).
    """
    cases = {
        "noscript": "<noscript><p>x</p></noscript>",
        "video": '<video><source src="a"><track kind="subtitles"></video>',
        "template": "<template><div>y</div></template>",
        "form": "<form><label>L</label><input><button>b</button></form>",
    }
    for name, src in cases.items():
        out, v = whitelist.filter_html(src)  # must not raise
        assert isinstance(out, str), f"{name}: expected a string output"
        assert f"<{name}" not in out, f"{name}: dropped parent leaked into output"
        assert any("dropped" in s for s in v), (
            f"{name}: expected at least one 'dropped' violation"
        )


def test_sample_deck_fixture_washes_clean():
    """The committed sample deck (coding-agent output) must wash without
    leaving any platform-incompatible tag in the output."""
    deck = (
        Path(__file__).parent / "fixtures" / "sample_deck.html"
    ).read_text(encoding="utf-8")
    out, v = whitelist.filter_html(deck)
    assert "<script" not in out
    assert "<canvas" not in out
    assert "<iframe" not in out
    assert "<video" not in out
    assert "onclick" not in out
    assert "<!--" not in out
    assert v  # at least one violation reported (we expect several)
