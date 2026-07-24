"""GzhWash pipeline — the deterministic, ordered HTML tree transform.

This is the core primitive of the product (see ``mvp_plan.md`` §2). Given an
HTML string produced by a coding agent (Claude Code, Cursor, or any HTML-deck
Skill) and a :class:`GzhCtx`, it produces a :class:`GzhArtifact` that satisfies
*two* constraints simultaneously:

1. The 公众号 editor can paste it without stripping tags / attrs / images.
2. The creator can edit a single character in-place in the editor without
   round-tripping back through the agent.

m1 runs the first two stages (whitelist + fonts) locally with no network.
The third stage (cdn replace) is an m2 stub — it is wired into the pipeline
so callers see the full contract, but raises :class:`NotImplementedError`
until the 公众号 API client ships.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from . import whitelist, fonts


# --- the primitive ----------------------------------------------------------


@dataclass(frozen=True)
class GzhCtx:
    """Immutable wash context — the rules the pipeline runs under.

    Fields default to the public 公众号 editor whitelist; callers override
    only what they need (e.g. a stricter enterprise policy or a relaxed one
    once the 公众号 platform rules loosen — see the m2 kill-gate in
    ``mvp_plan.md`` §5).
    """

    appid: str = ""
    secret: str = ""
    whitelisted_tags: frozenset[str] = whitelist.ALLOWED_TAGS
    allowed_attrs: Mapping = field(default_factory=lambda: whitelist.ALLOWED_ATTRS)
    allowed_fonts: frozenset[str] = fonts.ALLOWED_FONTS
    upload_cdn: bool = False  # m2 gate — when True, the cdn stage runs


@dataclass
class GzhArtifact:
    """Result of a :func:`wash` call."""

    html: str
    replaced_imgs: list[dict[str, str]] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# --- the pipeline -----------------------------------------------------------


def wash(
    html: str,
    ctx: GzhCtx | None = None,
    *,
    upload_cdn: bool | None = None,
) -> GzhArtifact:
    """Run the full GzhWash pipeline on ``html``.

    Stages, in order (the order is load-bearing — each stage operates on the
    output of the previous):

    1. ``whitelist.filter_html`` — drop platform-incompatible tags, strip
       non-allowlisted attributes (including all ``on*``), drop comments.
    2. ``fonts.normalize_fonts`` — rewrite inline ``font-family`` to the
       公众号-allowed set, preserving sans/serif/mono intent.
    3. ``cdn.replace`` *(m2 stub)* — download external ``<img src>`` and POST
       to the 公众号 CDN API, rewrite ``src``. Only runs when
       ``upload_cdn=True``; m1 always passes ``False``.

    Returns a :class:`GzhArtifact` with the washed HTML and a list of
    violations/notes (the union of all stages' diagnostics — useful for a
    ``--verbose`` flag and for the demo's progress output).
    """
    ctx = ctx or GzhCtx()
    if upload_cdn is None:
        upload_cdn = ctx.upload_cdn

    artifact = GzhArtifact(html="")

    # stage 1 — whitelist
    html, v = whitelist.filter_html(html)
    artifact.violations.extend(v)

    # stage 2 — fonts
    html, n = fonts.normalize_fonts(html)
    artifact.notes.extend(n)

    # stage 3 — cdn (m2 stub)
    if upload_cdn:
        from .cdn import replace as _cdn_replace  # lazy — keeps m1 net-free
        html, replaced, v = _cdn_replace(html, ctx)
        artifact.replaced_imgs.extend(replaced)
        artifact.violations.extend(v)

    artifact.html = html
    return artifact


__all__ = ["GzhCtx", "GzhArtifact", "wash"]
