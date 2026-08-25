"""公众号 HTML tag/attribute whitelist — the hard floor of the seam.

The 公众号 native editor enforces a conservative HTML subset: a fixed tag
whitelist, a fixed attribute whitelist (mostly ``style`` + media src/alt), and
zero ``on*`` event handlers. Pasting HTML that violates the whitelist results in
silent tag/attr stripping — the layout collapses and the creator has to fall
back to re-running the agent. This module is the deterministic translation that
pre-empts the strip.

The whitelist here is a *conservative* subset derived from observed 公众号
editor behavior. It is intentionally narrower than what some decks ship
(``<canvas>``, ``<iframe>``, ``<script>`` are dropped outright; ``<video>``
and ``<audio>`` are dropped too — the 公众号 editor does not accept them in
article body). Schema is remote-platform and unverifiable locally — field-check
before relying on it for production (see ``mvp_plan.md`` §5 m2 kill-gate).
"""

from __future__ import annotations

from typing import Iterable, Mapping

from bs4 import BeautifulSoup, Tag, NavigableString, Comment

# --- tag whitelist ----------------------------------------------------------

#: Tags the 公众号 editor accepts in article body. Anything else is either
#: unwrapped (contents lifted into the parent) or dropped (contents discarded)
#: — see :data:`DROP_TAGS` for the drop-list.
ALLOWED_TAGS: frozenset[str] = frozenset(
    {
        # structure
        "section", "div", "span", "p", "br", "hr",
        # headings
        "h1", "h2", "h3", "h4", "h5", "h6",
        # lists
        "ul", "ol", "li",
        # emphasis
        "strong", "b", "em", "i", "u", "s", "del", "ins", "sub", "sup", "small",
        "mark",
        # tables
        "table", "thead", "tbody", "tfoot", "tr", "td", "th", "caption",
        "colgroup", "col",
        # media (src must be 公众号 CDN for <img>; enforced in cdn stage)
        "img", "figure", "figcaption",
        # links (公众号 strips href in body except in some contexts; we keep
        # the tag so the editor can decide)
        "a",
        # code (often stripped by the editor, but harmless to keep)
        "pre", "code",
        # blockquote
        "blockquote",
    }
)

#: Tags whose *contents* are also discarded (not lifted into parent). These are
#: either actively dangerous (``script``), platform-incompatible
#: (``canvas``, ``iframe``, ``video``, ``audio``, ``object``, ``embed``), or
#: meta/structural noise from a coding-agent's HTML scaffold
#: (``style``, ``link``, ``meta``, ``base``, ``title``). Note: ``html``,
#: ``body``, ``head`` are intentionally NOT in this set — they fall through to
#: the "non-allowlisted" branch below and are *unwrapped* (contents lifted into
#: the parent), so the article body they wrap survives the wash. Decomposing
#: them would kill their children, breaking the edit-loop contract.
DROP_TAGS: frozenset[str] = frozenset(
    {
        "script", "style", "noscript", "template",
        "canvas", "svg", "math",
        "iframe", "video", "audio", "source", "track",
        "object", "embed", "applet", "param",
        "form", "input", "button", "textarea", "select", "option", "label",
        "fieldset", "legend", "optgroup", "datalist", "output", "progress",
        "meter",
        "link", "meta", "base", "title",
        "frame", "frameset", "noframes",
        "portal",
    }
)

# --- attribute whitelist ----------------------------------------------------

#: Attributes the 公众号 editor tolerates on the tags above. Anything else is
#: dropped. ``style`` survives (with its CSS subset normalized in :mod:`fonts`);
#: ``on*`` event handlers are always dropped (they are stripped by the editor
#: anyway and are an XSS smell).
ALLOWED_ATTRS: Mapping[str, frozenset[str]] = {
    "*": frozenset({"style", "class", "id", "title", "align"}),
    "img": frozenset({"src", "alt", "width", "height", "style", "class"}),
    "a": frozenset({"href", "title", "style", "class"}),
    "table": frozenset({"border", "cellpadding", "cellspacing", "style", "class", "width"}),
    "td": frozenset({"colspan", "rowspan", "style", "class", "align", "valign", "width", "height"}),
    "th": frozenset({"colspan", "rowspan", "style", "class", "align", "valign", "scope", "width", "height"}),
    "col": frozenset({"span", "style", "width"}),
    "colgroup": frozenset({"span", "style", "width"}),
    "ol": frozenset({"start", "type", "style", "class"}),
    "ul": frozenset({"style", "class"}),
    "br": frozenset({"clear"}),
    "hr": frozenset({"style", "class"}),
}

#: CSS properties allowed inside inline ``style``. The 公众号 editor allows a
#: rich inline-style subset (it is how 秀米/135 style content) — we keep a
#: generous allow-list and normalize ``font-family`` separately in
#: :mod:`gzhseam.fonts`.
ALLOWED_STYLE_PROPS: frozenset[str] = frozenset(
    {
        "color", "background-color", "background",
        "font-size", "font-weight", "font-style", "font-family",
        "line-height", "letter-spacing", "text-indent",
        "text-align", "text-decoration", "text-transform",
        "margin", "margin-top", "margin-bottom", "margin-left", "margin-right",
        "padding", "padding-top", "padding-bottom", "padding-left", "padding-right",
        "border", "border-top", "border-bottom", "border-left", "border-right",
        "border-color", "border-width", "border-style", "border-radius",
        "width", "height", "max-width", "min-width", "max-height", "min-height",
        "display", "float", "clear",
        "list-style", "list-style-type",
        "vertical-align", "white-space", "word-break", "word-spacing",
        "box-sizing", "opacity",
        "box-shadow",
    }
)


# ---------------------------------------------------------------------------


def _attr_allowed(
    tag_name: str,
    attr_name: str,
    allowed_attrs: Mapping[str, frozenset[str]] = ALLOWED_ATTRS,
) -> bool:
    """Whether ``attr_name`` is allowed on ``tag_name`` per the whitelist."""
    name = attr_name.lower()
    if name.startswith("on"):  # event handlers always stripped
        return False
    allowed = allowed_attrs.get(tag_name, allowed_attrs["*"])
    return name in allowed


def _filter_attrs(
    tag: Tag,
    allowed_attrs: Mapping[str, frozenset[str]] = ALLOWED_ATTRS,
) -> dict[str, str]:
    """Return the dict of attributes on ``tag`` that survive the whitelist.

    Style values are passed through untouched here; font normalization happens
    in :mod:`gzhseam.fonts` as a separate pipeline stage so the two concerns
    stay separable and independently testable.
    """
    out: dict[str, str] = {}
    for name, value in tag.attrs.items():
        if _attr_allowed(tag.name, name, allowed_attrs):
            out[name] = value
    return out


#: Tags BeautifulSoup's lxml parser synthesizes around any fragment
#: (``<html><body>...</body></html>``). They are *parser scaffolding*, not
#: input violations — we unwrap them silently so the violation list reports
#: only real agent-HTML drift, and the second pass is violation-free
#: (idempotency contract).
PARSER_SCAFFOLD_TAGS: frozenset[str] = frozenset({"html", "body", "head"})


def _drop_disallowed_tags(
    soup: BeautifulSoup,
    allowed_tags: frozenset[str] = ALLOWED_TAGS,
) -> list[str]:
    """Walk the tree and remove/unwrap tags per ``allowed_tags`` (default :data:`ALLOWED_TAGS`) / :data:`DROP_TAGS`.

    Returns the list of violation descriptions (for :class:`GzhArtifact`).
    Dropped-content tags (``script``/``canvas``/``iframe``/...) are removed
    with their contents; other non-allowed tags (e.g. agent's ``<div
    data-agent="...">`` scaffold wrappers) are *unwrapped* — contents lifted
    into the parent so the visible body survives. ``<html>/<body>/<head>``
    are parser scaffolding and are skipped silently (not reported as
    violations, not unwrapped) so the second pass is violation-free; the
    serializer (:func:`filter_html`) emits only the body's inner HTML so
    these wrappers never reach the output.
    """
    violations: list[str] = []
    # iterate over a static list — we mutate the tree as we go.
    for tag in list(soup.find_all(True)):
        # bs4 ``decompose()`` (called on a DROP_TAG parent below) recursively
        # destroys descendants: it blanks ``.name`` and orphans them from the
        # tree. The snapshot above still holds those destroyed tags, so a later
        # iteration would otherwise call ``.unwrap()`` on a tree-detached tag
        # and raise ``ValueError`` — crashing the entire wash with NO output on
        # ordinary coding-agent HTML like ``<noscript><p>…</p></noscript>``,
        # ``<video><source>…</video>``, ``<template>…</template>``,
        # ``<form>…</form>``. Skip any tag already destroyed/detached by an
        # earlier ``decompose()`` in this same pass.
        if getattr(tag, "decomposed", False) or tag.parent is None:
            continue
        name = tag.name
        if name in PARSER_SCAFFOLD_TAGS:
            # parser scaffolding — leave in tree, serializer drops it.
            continue
        if name in DROP_TAGS:
            violations.append(f"dropped <{name}> (platform-incompatible)")
            tag.decompose()
            continue
        if name not in allowed_tags:
            violations.append(f"unwrapped <{name}> (not in whitelist)")
            tag.unwrap()
            continue
    return violations


def _drop_disallowed_attrs(
    soup: BeautifulSoup,
    allowed_tags: frozenset[str] = ALLOWED_TAGS,
    allowed_attrs: Mapping[str, frozenset[str]] = ALLOWED_ATTRS,
) -> list[str]:
    """Strip non-allowlisted attributes (including all ``on*``) in place."""
    violations: list[str] = []
    for tag in soup.find_all(True):
        if tag.name not in allowed_tags:
            continue  # already unwrapped/dropped
        kept: dict[str, str] = _filter_attrs(tag, allowed_attrs)
        dropped = [k for k in tag.attrs if k not in kept]
        if dropped:
            violations.append(
                f"<{tag.name}>: stripped attrs {sorted(dropped)}"
            )
        tag.attrs = kept
    return violations


def _strip_comments(soup: BeautifulSoup) -> list[str]:
    """Drop HTML comments (the editor ignores them and they bloat paste)."""
    n = 0
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
        n += 1
    return [f"removed {n} HTML comment(s)"] if n else []


def _serialize_fragment(soup: BeautifulSoup) -> str:
    """Emit only the article body — strip the ``<!DOCTYPE>``/``<html>``/
    ``<body>``/``<head>`` scaffolding the lxml parser synthesizes around any
    fragment. Output is a pure fragment, the shape the 公众号 editor expects
    on paste.

    If the document has a ``<body>`` tag (the normal case — lxml synthesizes
    one around any fragment with body-level elements), serialize its inner
    HTML. When lxml created no ``<body>`` — which happens when the input
    contained only head-level elements (``script``/``style``/``meta``/
    ``title``/``link``, all :data:`DROP_TAGS`, decomposed earlier by
    :func:`_drop_disallowed_tags`) — there is no article content to emit,
    so return an empty fragment rather than leaking the
    ``<html><head></head></html>`` document wrapper the wash is
    contractually supposed to strip.
    """
    if soup.body is None:
        return ""
    return soup.body.decode_contents().strip()


def filter_html(
    html: str,
    *,
    allowed_tags: frozenset[str] = ALLOWED_TAGS,
    allowed_attrs: Mapping[str, frozenset[str]] = ALLOWED_ATTRS,
) -> tuple[str, list[str]]:
    """Run the whitelist stage: tag drop/unwrap + attribute strip + comment strip.

    ``allowed_tags`` / ``allowed_attrs`` default to the module-level
    :data:`ALLOWED_TAGS` / :data:`ALLOWED_ATTRS`, so a bare
    ``filter_html(html)`` call is unchanged. Pass them to apply a per-call
    policy (e.g. a stricter enterprise no-``<a>`` allowlist, or a relaxed one
    once the platform rules loosen) — the overrides *replace* the defaults,
    they are not merged with them.

    Returns ``(washed_html, violations)``. Idempotent: running twice produces
    the same output and zero new violations on the second pass.

    The returned HTML is a fragment (no ``<html>/<head>/<body>`` wrapper, no
    ``<!DOCTYPE>``) — that is the shape the 公众号 editor expects on paste.
    """
    if not html or not html.strip():
        return "", ["empty input"]
    soup = BeautifulSoup(html, "lxml")
    violations: list[str] = []
    violations += _drop_disallowed_tags(soup, allowed_tags)
    violations += _strip_comments(soup)
    violations += _drop_disallowed_attrs(soup, allowed_tags, allowed_attrs)
    out = _serialize_fragment(soup)
    return out, violations


__all__ = [
    "ALLOWED_TAGS",
    "DROP_TAGS",
    "ALLOWED_ATTRS",
    "ALLOWED_STYLE_PROPS",
    "filter_html",
]
