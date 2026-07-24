"""Image CDN replacement — the third wash stage (m2).

The 公众号 editor strips external ``<img src>`` URLs on paste: only
CDN-hosted images survive. The m2 stage downloads each external image, POSTs
it to the 公众号 material upload API (``/cgi-bin/media/upload``), and rewrites
the ``src`` to the returned 公众号 CDN URL. The wash pipeline calls this stage
only when ``GzhCtx.upload_cdn=True`` (m1 always passes ``False`` — m1 is pure
local with no network).

This module is a deliberate stub at m1. It raises :class:`NotImplementedError`
on call so the contract is visible end-to-end but m1 cannot accidentally ship
a network call. Implementation lands in m2 behind the kill-gate described in
``mvp_plan.md`` §5 (field-check 公众号 rules before starting; if the platform
has stopped stripping external images, the moat collapses and m2 is killed).

Planned m2 contract::

    def replace(html: str, ctx: GzhCtx) -> tuple[str, list[dict], list[str]]:
        ...

    Returns ``(washed_html, replaced_imgs, violations)`` where
    ``replaced_imgs`` is ``[{"ext": <original URL>, "cdn": <公众号 URL>}, ...]``
    matching :data:`GzhArtifact.replaced_imgs`.

Planned m2 implementation notes (preserved here so m2 has a starting point):
    - use httpx for the image download + the 公众号 API POST
    - cache by content-hash to skip re-uploading identical images
    - exponential backoff on 公众号 45009 rate-limit (access_token 频控)
    - access_token cached ~90 min via :mod:`gzhseam.api.auth`
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .washer import GzhCtx


def replace(html: str, ctx: "GzhCtx | None" = None) -> tuple[str, list[dict], list[str]]:
    """m2 stub — replace external ``<img src>`` with 公众号 CDN URLs.

    Raises :class:`NotImplementedError` at m1. Callers should set
    ``upload_cdn=False`` (the default) to keep the pipeline local; the
    CLI's ``--cdn`` flag flips this on and currently errors with a clear
    message pointing at the m2 roadmap entry.
    """
    raise NotImplementedError(
        "cdn.replace is the m2 stage (公众号 material upload API). "
        "m1 ships local-only wash; pass --no-cdn (the default) or see "
        "mvp_plan.md §5 m2 for the m2 roadmap."
    )


__all__ = ["replace"]
