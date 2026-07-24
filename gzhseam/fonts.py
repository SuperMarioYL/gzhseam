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


_STYLE_RE = re.compile(r"font-family\s*:\s*([^;]+)", re.IGNORECASE)
_DECL_RE = re.compile(r"([^:]+?)\s*:\s*([^;]+)")


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


def _nearest_family(agent_chain: str) -> str:
    """Map an agent-emitted ``font-family`` value to a 公众号-allowed chain.

    Strategy: keep any allowed token from the agent's chain (preserving order,
    so the agent's first preference that the editor can render wins); if none
    survive, substitute the default chain for the bucket of the *first* token
    in the agent's chain — so a deck styled with ``"Fira Code"`` resolves to
    the mono default rather than collapsing to body sans.
    """
    tokens = [t.strip() for t in agent_chain.split(",") if t.strip()]
    kept = [t for t in tokens if t.strip("'\"") in ALLOWED_FONTS]
    if kept:
        return ", ".join(kept)
    if not tokens:
        return ", ".join(BUCKET_DEFAULTS["sans"])
    bucket = _classify_token(tokens[0])
    return ", ".join(BUCKET_DEFAULTS[bucket])


def normalize_style(style: str) -> tuple[str, list[str]]:
    """Normalize one inline ``style`` string.

    Returns ``(new_style, notes)``. Re-maps every ``font-family`` declaration
    to an allowed chain; leaves other declarations untouched (the CSS
    property whitelist is enforced by :mod:`gzhseam.whitelist`).
    """
    if not style:
        return "", []
    notes: list[str] = []
    out_decls: list[str] = []
    for key, val in _DECL_RE.findall(style):
        k = key.strip().lower()
        v = val.strip()
        if k == "font-family":
            new = _nearest_family(v)
            if new != v:
                notes.append(f"font-family: {v!r} -> {new!r}")
            out_decls.append(f"font-family: {new}")
        else:
            out_decls.append(f"{key.strip()}: {v}")
    return "; ".join(out_decls), notes


def normalize_fonts(html: str) -> tuple[str, list[str]]:
    """Run the font stage on an HTML fragment.

    Walks every tag with a ``style`` attribute and rewrites each
    ``font-family`` declaration to a 公众号-allowed chain. Idempotent: a
    second pass on already-normalized HTML produces zero notes.

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
        new, n = normalize_style(style)
        if n:
            notes.extend(n)
            tag["style"] = new
    container = soup.body or soup
    return container.decode_contents().strip(), notes


__all__ = [
    "ALLOWED_FONTS",
    "BUCKET_DEFAULTS",
    "normalize_style",
    "normalize_fonts",
]
