"""Tests for the GzhSeam CLI (:mod:`gzhseam.cli`).

Covers the v0.2.0 ``feat-feedback-surface-for-cloners`` contract:

- ``gzhseam feedback`` prints the project's GitHub issues URL and exits 0;
- in a non-TTY (the test runner) :func:`webbrowser.open` is NOT called — the
  printed URL is the source of truth and the browser is only touched when
  stdout is a real TTY;
- a successful ``wash`` run that uploaded >0 CDN images prints the feedback
  nudge line (wired inert in m1/v0.2.0 — the m2 cdn stage is a stub, so the
  nudge is exercised here by stubbing the pipeline to return a populated
  ``replaced_imgs`` list);
- a local-only ``wash`` (no CDN upload) does NOT print the nudge.
"""

from __future__ import annotations

import sys
from pathlib import Path

from click.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gzhseam import cli as cli_mod  # noqa: E402
from gzhseam.washer import GzhArtifact  # noqa: E402


def test_feedback_prints_issues_url_and_exits_zero():
    r = CliRunner().invoke(cli_mod.cli, ["feedback"])
    assert r.exit_code == 0
    assert "github.com/SuperMarioYL/gzhseam/issues" in r.output


def test_feedback_does_not_open_browser_in_non_tty(monkeypatch):
    """In the CliRunner stdout is not a TTY, so ``webbrowser.open`` must not
    fire — the printed URL is the source of truth and we never touch the
    browser on a headless / piped context."""
    opened: list[str] = []
    monkeypatch.setattr(
        cli_mod.webbrowser, "open", lambda url: opened.append(url) or False
    )
    r = CliRunner().invoke(cli_mod.cli, ["feedback"])
    assert r.exit_code == 0
    assert opened == []


def test_wash_prints_feedback_nudge_when_cdn_images_uploaded(tmp_path, monkeypatch):
    """The post-wash nudge fires only when the wash actually uploaded CDN
    images (a real user, not a dry-run). Stub the pipeline to return a
    populated ``replaced_imgs`` and assert the nudge line appears.

    Inert in m1/v0.2.0 by default — the m2 cdn stage raises
    :class:`NotImplementedError`, so ``replaced_imgs`` is never populated on
    a real run; this test pins the wiring so the nudge lights up the moment
    m2 ships real uploads.
    """
    deck = tmp_path / "deck.html"
    deck.write_text("<p>x</p>", encoding="utf-8")
    out = tmp_path / "out.html"

    def fake_wash(html, ctx):
        return GzhArtifact(
            html=html,
            replaced_imgs=[{"ext": "http://x.invalid/a.png", "cdn": "CDN_URL"}],
        )

    monkeypatch.setattr(cli_mod, "_wash_pipeline", fake_wash)
    r = CliRunner().invoke(cli_mod.cli, ["wash", str(deck), "-o", str(out), "--cdn"])
    assert r.exit_code == 0, r.output
    assert "gzhseam feedback" in r.output


def test_wash_no_nudge_on_local_dry_run(tmp_path):
    """A local-only wash (no CDN upload) must NOT print the feedback nudge —
    the nudge targets real users whose wash actually hit the CDN."""
    deck = tmp_path / "deck.html"
    deck.write_text("<p>hi</p>", encoding="utf-8")
    out = tmp_path / "out.html"
    r = CliRunner().invoke(cli_mod.cli, ["wash", str(deck), "-o", str(out)])
    assert r.exit_code == 0, r.output
    assert "gzhseam feedback" not in r.output
