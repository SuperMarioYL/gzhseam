"""GzhSeam — a CLI seam between coding-agent HTML and the 公众号 native editor.

The product takes HTML produced by a coding agent (Claude Code, Cursor, or any
HTML-deck Skill) and washes it into a 公众号-editor-pasteable, in-place-editable
HTML asset: tag-whitelist compliant, font-constraint compliant, and (in m2)
images re-hosted on the 公众号 CDN.

m1 is fully local (no network): tag-whitelist filter + font normalize.
m2/m3 are stubs.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
