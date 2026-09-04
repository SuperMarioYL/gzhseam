"""Font-constraint normalization — the second wash stage.

The 公众号 editor renders with a constrained system-font set: web-fonts and
exotic font-family chains (``"Fira Code"``, ``"Operator Mono"``, agent-shipped
``@font-face`` declarations) get silently reset to the editor default, which
breaks the deck's typographic hierarchy on paste. This stage rewrites inline
``font-family`` declarations on every surviving tag so that whatever the
coding-agent emitted maps to the nearest *公众号-allowed* family, preserving
the intent (serif vs sans vs monospace) without depending on fonts the editor
cannot render.

This module only touches inline ``style`` attributes — it does not touch
``<style>`` blocks (those are dropped by :mod:`gzhseam.whitelist`, since the
公众号 editor strips them anyway and the agent's CSS is not platform-portable).
"""

from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup, Tag

# --- allowed font families (公众号 editor subset) -------------------------

#: The set of font-family tokens the 公众号 editor renders without resetting.
#: Three buckets: sans (default body), serif (headings / formal copy), and
#: monospace (code). Everything else maps into one of these in
#: :func:`_nearest_family` so the author's *intent* (serif vs sans vs mono)
#: survives even when the literal font name does not.
ALLOWED_FONTS: frozenset[str] = frozenset(
    {
        # generic — always safe
        "sans-serif", "serif", "monospace", "cursive", "fantasy",
        # CN-safe system sans
        "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei",
        "Heiti SC", "STHeiti", "SimHei",
        # CN-safe system serif
        "Songti SC", "STSong", "SimSun", "STKaiti", "KaiTi",
        # EN system sans/serif
        "Helvetica Neue", "Helvetica", "Arial",
        "Times New Roman", "Times",
        "Georgia",
        "Verdana", "Tahoma", "Trebuchet MS",
        "Inter", "system-ui", "ui-sans-serif", "ui-serif", "ui-monospace",
        # monospace
        "Menlo", "Monaco", "Consolas", "Courier New", "Courier",
        "monospace",
    }
)

#: Canonical fallback chains per bucket. Used when the agent's chain has no
#: allowed member: we substitute the bucket default so the *visual role*
#: (body sans / heading serif / code mono) is preserved.
BUCKET_DEFAULTS: dict[str, list[str]] = {
    "sans": ["PingFang SC", "Microsoft YaHei", "Helvetica Neue", "Arial", "sans-serif"],
    "serif": ["Songti SC", "STSong", "Georgia", "serif"],
    "mono": ["Menlo", "Monaco", "Consolas", "Courier New", "monospace"],
}

#: Heuristics for classifying an arbitrary font-family token into a bucket.
#: Checked in order; first match wins. Lower-case compare.
SERIF_HINTS: tuple[str, ...] = ("serif", "song", "simsun", "stsong", "georgia", "times", "kai", "roman")
SANS_HINTS: tuple[str, ...] = ("sans", "pingfang", "yahei", "heiti", "helvetica", "arial", "inter", "system-ui", "ui-sans", "verdana", "tahoma", "trebuchet", "lucida")
MONO_HINTS: tuple[str, ...] = ("mono", "menlo", "monaco", "consolas", "courier", "fira code", "jetbrains", "operator mono", "source code", "ui-monospace", "sf mono")


#: Matches a single ``font-family`` *declaration* — and ONLY a real
#: declaration, not the literal ``font-family:`` text that may appear inside a
#: quoted CSS value (e.g. ``content: "font-family: bar"``). v0.6.0
#: ``fix-font-family-regex-matches-inside-quoted-css-values``: the v0.2.0 regex
#: ``(font-family\s*:\s*)([^;]+)`` matched ``font-family:`` ANYWHERE in the
#: style string, so a font-family token inside a quoted ``content`` value
#: co-occurring with a real font-family remap was also matched; ``[^;]+`` then
#: ate the content value's closing quote and the replacement dropped it, leaving
#: the string unclosed and swallowing every subsequent declaration into it. The
#: leading ``(?:^|;)\s*`` group now anchors the match to a declaration boundary
#: (start-of-string or after a ``;``), so a ``font-family:`` whose preceding
#: character is a quote is never matched. Capture groups: (1) the leading
#: separator (``""`` at start-of-string, or ``";"`` + whitespace — preserved
#: verbatim on splice-back so the ``;`` is not lost), (2) the
#: ``font-family\s*:\s*`` prefix (original spacing around the colon preserved),
#: (3) the value up to the next ``;`` or end-of-string. ``font-family`` values
#: never legitimately contain ``;`` (CSS uses ``,`` to separate family names,
#: not ``;``), so ``[^;]+`` is safe here — and a ``;`` inside a data-URL
#: ``background`` value is never at a font-family declaration boundary, so the
#: v0.2.0 data-URL fix is not regressed.
_FONT_FAMILY_RE = re.compile(
    r"((?:^|;)\s*)(font-family\s*:\s*)([^;]+)", re.IGNORECASE
)


def _classify_token(tok: str) -> str:
    """Bucket one font-family token as ``sans``/``serif``/``mono``.

    Defaults to ``sans`` (the body default for 公众号 article copy).
    """
    t = tok.lower().strip().strip("'\"")
    if any(h in t for h in MONO_HINTS):
        return "mono"
    if any(h in t for h in SERIF_HINTS):
        return "serif"
    if any(h in t for h in SANS_HINTS):
        return "sans"
    return "sans"  # safe default for CN article body


def _nearest_family(
    agent_chain: str,
    allowed_fonts: frozenset[str] = ALLOWED_FONTS,
) -> str:
    """Map an agent-emitted ``font-family`` value to a 公众号-allowed chain.

    Strategy: keep any allowed token from the agent's chain (preserving order,
    so the agent's first preference that the editor can render wins); if none
    survive, substitute the default chain for the bucket of the *first* token
    in the agent's chain — so a deck styled with ``"Fira Code"`` resolves to
    the mono default rather than collapsing to body sans.
    """
    tokens = [t.strip() for t in agent_chain.split(",") if t.strip()]
    kept = [t for t in tokens if t.strip("'\"") in allowed_fonts]
    if kept:
        return ", ".join(kept)
    if not tokens:
        return ", ".join(BUCKET_DEFAULTS["sans"])
    bucket = _classify_token(tokens[0])
    return ", ".join(BUCKET_DEFAULTS[bucket])


def normalize_style(
    style: str,
    allowed_fonts: frozenset[str] = ALLOWED_FONTS,
) -> tuple[str, list[str]]:
    """Normalize one inline ``style`` string.

    Returns ``(new_style, notes)``. Re-maps every ``font-family`` declaration
    to an allowed chain and leaves every *other* declaration **verbatim** —
    the style string is spliced around the font-family matches, never
    re-parsed through a ``;``-splitting regex, so values that legitimately
    contain ``;`` (data-URL ``background``, quoted ``content`` strings)
    survive a co-occurring font-family remap intact. The CSS property
    whitelist is enforced by :mod:`gzhseam.whitelist`.

    v0.6.0 ``fix-font-family-regex-matches-inside-quoted-css-values``: the
    font-family regex is anchored to a declaration boundary
    (start-of-string or after a ``;``), so the literal ``font-family:`` text
    inside a quoted value (e.g. ``content: "font-family: bar"``) is never
    matched — only real ``font-family`` declarations are remapped. The CSS
    property whitelist is enforced by :mod:`gzhseam.whitelist`.

    Idempotent: a second pass on already-normalized HTML produces zero notes,
    because a remapped chain consists solely of allowed tokens.
    """
    if not style:
        return "", []
    notes: list[str] = []

    def _remap_font_family(m: re.Match[str]) -> str:
        lead, prefix, val = m.group(1), m.group(2), m.group(3)
        stripped = val.strip()
        new = _nearest_family(stripped, allowed_fonts)
        if new != stripped:
            notes.append(f"font-family: {stripped!r} -> {new!r}")
        return f"{lead}{prefix}{new}"

    new_style = _FONT_FAMILY_RE.sub(_remap_font_family, style)
    return new_style, notes


def normalize_fonts(
    html: str,
    *,
    allowed_fonts: frozenset[str] = ALLOWED_FONTS,
) -> tuple[str, list[str]]:
    """Run the font stage on an HTML fragment.

    Walks every tag with a ``style`` attribute and rewrites each
    ``font-family`` declaration to a 公众号-allowed chain. Idempotent: a
    second pass on already-normalized HTML produces zero notes.

    ``allowed_fonts`` defaults to the module-level :data:`ALLOWED_FONTS`;
    pass it to admit fonts the default set rejects (or to reject ones it
    keeps) for a single call, without changing the module constant.

    Returns a fragment (no ``<html>/<body>`` wrapper) so this stage is
    safe to chain after :func:`gzhseam.whitelist.filter_html` without
    re-introducing parser scaffolding.
    """
    if not html or not html.strip():
        return html or "", []
    soup = BeautifulSoup(html, "lxml")
    notes: list[str] = []
    for tag in soup.find_all(True):
        style = tag.get("style")
        if not style:
            continue
        new, n = normalize_style(style, allowed_fonts)
        if n:
            notes.extend(n)
            tag["style"] = new
    container = soup.body
    if container is None:
        # no <body> (head-only input) — no article content to emit; return
        # an empty fragment rather than leaking the <html><head> wrapper.
        return "", notes
    return container.decode_contents().strip(), notes


__all__ = [
    "ALLOWED_FONTS",
    "BUCKET_DEFAULTS",
    "normalize_style",
    "normalize_fonts",
]
