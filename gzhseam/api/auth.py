"""公众号 API authentication — access_token acquisition + caching (m2 stub).

The 公众号 Open API requires an ``access_token`` for every call. The token
is exchanged for AppID + AppSecret via ``/cgi-bin/token`` and is valid for
7200s (2h); the platform imposes a daily call-cap (45009 频控 on over-fetch)
so caching the token across washes is mandatory — re-fetching per image
upload blows the rate-limit fast.

This module is the m2 stub: it preserves the caching contract and points m2
at the implementation notes. m1 does not touch the network.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Default token cache location — matches the ``init`` command's credential dir.
DEFAULT_CACHE_DIR: Path = Path.home() / ".gzhseam"
#: Refresh proactively (90 min < 120 min lifetime) so a wash never hits a
#: mid-flight token-expiry retry storm.
DEFAULT_TTL_SAFETY_S: int = 1800


@dataclass
class TokenCache:
    """On-disk access_token cache.

    The cached token is treated as opaque (the 公众号 API does not document
    a way to validate a token without spending one API call, so we just
    trust the cached value until its TTL + safety-margin elapses).
    """

    cache_dir: Path = DEFAULT_CACHE_DIR
    safety_s: int = DEFAULT_TTL_SAFETY_S

    @property
    def cache_file(self) -> Path:
        return self.cache_dir / "access_token.json"

    def get(self) -> Optional[str]:
        """Return a fresh cached token or ``None`` if expired/missing.

        m2 stub — returns ``None``. The m2 implementation reads
        ``self.cache_file``, parses ``{"token": ..., "expires_at": <epoch>}``,
        and returns the token if ``now < expires_at - safety_s``.
        """
        raise NotImplementedError(
            "TokenCache.get is the m2 stage. m1 ships local-only wash; "
            "auth runs only when --cdn is set (mvp_plan.md §5 m2)."
        )

    def put(self, token: str, expires_in: int) -> None:
        """Cache ``token`` with expiry ``time.time() + expires_in``.

        m2 stub — raises :class:`NotImplementedError`.
        """
        raise NotImplementedError(
            "TokenCache.put is the m2 stage. m1 ships local-only wash."
        )


__all__ = ["TokenCache", "DEFAULT_CACHE_DIR", "DEFAULT_TTL_SAFETY_S"]
