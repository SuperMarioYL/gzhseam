"""公众号 Open API client (m2 stub).

The m2 wash stage uses this client to upload material to the 公众号 CDN and
to read the access-token it needs for that upload. The contract is preserved
here so m2 has a clear shape to fill in. m1 does not touch the network.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GzhClient:
    """Thin client over the 公众号 Open API.

    Holds the resolved base URL + an :class:`~gzhseam.api.auth.TokenCache`
    and exposes only the calls GzhSeam needs:

    - :meth:`upload_image` — POST a binary image to
      ``/cgi-bin/media/upload`` and return the resulting CDN URL.
    - :meth:`material_add` — for images that should persist as permanent
      material (公众号 distinguishes temporary vs permanent material; the
      CDN URL returned for permanent material does not expire).

    All schema is remote-platform and unverifiable locally (see plan
    frontmatter ``schema_unverified``); m2 must field-check current rules
    before relying on these endpoints.
    """

    appid: str
    secret: str
    base_url: str = "https://api.weixin.qq.com"

    def upload_image(self, image_bytes: bytes, filename: str = "img.png") -> str:
        """Upload a single image to 公众号 CDN; return the CDN URL.

        m2 stub — raises :class:`NotImplementedError`. The m2 implementation
        will use httpx to POST ``multipart/form-data`` to
        ``/cgi-bin/media/upload?type=image`` with the cached access_token,
        parse the JSON response (``{"media_id": "...", "url": "..."}`` for
        permanent material), and return ``url``.
        """
        raise NotImplementedError(
            "GzhClient.upload_image is the m2 stage. m1 ships local-only wash."
        )

    def material_add(self, image_bytes: bytes, filename: str = "img.png") -> str:
        """Add a permanent material; return the non-expiring CDN URL.

        m2 stub — same as :meth:`upload_image` for now.
        """
        raise NotImplementedError(
            "GzhClient.material_add is the m2 stage. m1 ships local-only wash."
        )


__all__ = ["GzhClient"]
