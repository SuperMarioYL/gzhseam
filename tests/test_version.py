"""Version-lockstep test — every version surface must agree.

Pins the single-source-of-truth invariant: the ``VERSION`` file, the package
``__version__``, the ``pyproject.toml`` ``[project] version``, and the CLI
``--version`` output must all report the same version string. A drift here
(e.g. a release that bumps ``pyproject.toml`` but forgets ``VERSION``) is the
canonical silent-release defect this guard catches going forward.

``web/site.json`` carries no ``content_version`` field (its keys are
schema/name/github/host/lang/accent/hero/advantages/scene/cta/footer; the Pages
workflow rebuilds on any ``web/**`` push, not on a version field), so it is not
part of the lockstep — there is no site-side version number to drift.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from click.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gzhseam import __version__  # noqa: E402
from gzhseam import cli as cli_mod  # noqa: E402


def _read_version_file() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _read_pyproject_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def _read_cli_version() -> str:
    r = CliRunner().invoke(cli_mod.cli, ["--version"])
    assert r.exit_code == 0, r.output
    # click version_option prints "gzhseam, version X.Y.Z"
    return r.output.strip().split()[-1]


def test_version_lockstep():
    """VERSION == __version__ == pyproject.toml version == CLI --version."""
    surfaces = {
        "VERSION file": _read_version_file(),
        "__version__": __version__,
        "pyproject.toml": _read_pyproject_version(),
        "CLI --version": _read_cli_version(),
    }
    distinct = set(surfaces.values())
    assert len(distinct) == 1, f"version surfaces drifted: {surfaces}"
