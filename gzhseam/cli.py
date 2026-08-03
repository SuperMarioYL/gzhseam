"""GzhSeam CLI — the user-facing entry point.

Subcommands:

- ``wash <deck.html> -o <out.html>`` — run the m1 wash (local, no network).
  The ``--cdn`` flag flips on the m2 stage, which currently errors with a
  clear "m2 not implemented" message instead of touching the network.
- ``init`` — m3 stub: prompt for 公众号 AppID/Secret and write
  ``~/.gzhseam/credentials.toml``.
- ``auth login`` — m2 stub: exchange AppID/Secret for an access_token and
  cache it.
- ``feedback`` — print the project's GitHub issues URL and (in a TTY) open
  it via stdlib :mod:`webbrowser`, so a cloner who hits one of the v0.2.0
  crash fixes can file a high-signal bug in under 60 seconds. Prefilled
  issue templates live in ``.github/ISSUE_TEMPLATE/``.

m1 is fully implemented for ``wash``. ``init`` and ``auth login`` raise
:class:`NotImplementedError` with a pointer to the roadmap — wiring them in
would be the m2/m3 work.
"""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

import click
from rich.console import Console

from . import __version__
from .washer import wash as _wash_pipeline, GzhCtx

console = Console()

#: Canonical project issues URL — the ``feedback`` subcommand opens this and
#: the post-wash nudge points here when a real CDN upload completed.
ISSUES_URL = "https://github.com/SuperMarioYL/gzhseam/issues"


def _split_and_count(path: Path) -> tuple[str, int]:
    """Read a single HTML file; return (text, img_count).

    img_count is reported by the demo's progress output ("1 个 deck, 12 张图").
    """
    text = path.read_text(encoding="utf-8")
    # cheap count — we don't parse here, just for the progress line.
    img_count = text.lower().count("<img")
    return text, img_count


@click.group()
@click.version_option(__version__, prog_name="gzhseam")
@click.help_option("-h", "--help")
def cli() -> None:
    """GzhSeam — wash coding-agent HTML into 公众号-native editable HTML."""


@cli.command()
@click.argument(
    "deck",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "-o", "--output",
    "output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("gzh-ready.html"),
    show_default=True,
    help="Output HTML path.",
)
@click.option(
    "--cdn/--no-cdn",
    default=False,
    show_default=True,
    help="Run the m2 CDN upload stage (m2 stub — raises NotImplementedError).",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Print per-stage violations and font-rewrite notes.",
)
def wash(deck: Path, output: Path, cdn: bool, verbose: bool) -> None:
    """Run the GzhWash pipeline on a single HTML deck."""
    text, img_count = _split_and_count(deck)
    console.print(f"[cyan]→ 解析 HTML[/cyan] (1 个 deck, {img_count} 张图)")
    console.print(
        "[cyan]→ 过滤标签白名单[/cyan] (移除 <script>, <canvas>, on* 事件)"
    )
    console.print(
        "[cyan]→ 字体规整[/cyan] (font-family → 公众号允许集)"
    )
    if cdn:
        console.print(
            f"[cyan]→ 上传 {img_count} 张图到公众号 CDN...[/cyan]"
        )
        # m2 path — let the pipeline call into the stub and raise a clear msg.
        try:
            artifact = _wash_pipeline(text, GzhCtx(upload_cdn=True))
        except NotImplementedError as e:
            console.print(f"[red]✗[/red] {e}")
            sys.exit(2)
    else:
        artifact = _wash_pipeline(text, GzhCtx(upload_cdn=False))

    output.write_text(artifact.html, encoding="utf-8")
    console.print(
        f"[green]✓[/green] {output} 已生成"
        + ("（图片全部走公众号 CDN，" if cdn else "（纯本地洗，")
        + "可直接贴入公众号编辑器就地改一个字）"
    )
    # Feedback nudge: only fires when the wash actually uploaded CDN images
    # (a real user, not a dry-run). Inert in m1/v0.2.0 — the m2 cdn stage is
    # a NotImplementedError stub, so ``replaced_imgs`` is never populated on
    # a successful run. The wiring is in place so the nudge lights up the
    # moment m2 ships real uploads.
    if artifact.replaced_imgs:
        console.print(
            "[dim]· 报告 bug 或提 feature request：运行 `gzhseam feedback`[/dim]"
        )
    if verbose:
        for line in artifact.violations:
            console.print(f"  [yellow]![/yellow] {line}")
        for line in artifact.notes:
            console.print(f"  [dim]·[/dim] {line}")


@cli.command()
def init() -> None:
    """Write ``~/.gzhseam/credentials.toml`` from interactive prompts (m3 stub)."""
    raise NotImplementedError(
        "gzhseam init is the m3 stage — interactive credential setup lands in "
        "mvp_plan.md §5 m3. m1 wash is local-only and needs no credentials."
    )


@cli.group(name="auth")
def auth_group() -> None:
    """公众号 API auth (m2 stub)."""


@auth_group.command(name="login")
def auth_login() -> None:
    """Exchange AppID/Secret for an access_token and cache it (m2 stub)."""
    raise NotImplementedError(
        "gzhseam auth login is the m2 stage — access_token caching lands in "
        "mvp_plan.md §5 m2. m1 wash is local-only and needs no auth."
    )


@cli.command()
def feedback() -> None:
    """Open the project's GitHub issues page to file a bug or feature request.

    Prints the issues URL and, when stdout is a TTY, opens it in the default
    browser via stdlib :mod:`webbrowser` (no new runtime dependency). Prefilled
    issue templates (``.github/ISSUE_TEMPLATE/bug_report.md``,
    ``.github/ISSUE_TEMPLATE/feature_request.md``) capture the repro fields
    (``gzhseam --version``, OS / Python, input HTML snippet, the exact
    ``gzhseam wash ...`` command, observed-vs-expected output) so a cloner
    who hits one of the v0.2.0-fixed crashes can file a high-signal issue in
    under 60 seconds.
    """
    console.print(f"[cyan]→[/cyan] 报告 bug 或提 feature request：{ISSUES_URL}")
    console.print(
        "[dim].github/ISSUE_TEMPLATE/ 下有预填模板，60 秒提一个高信号 issue。[/dim]"
    )
    if sys.stdout.isatty():
        # best-effort open — never fatal: webbrowser.open returns False on
        # headless/unsupported platforms, and we already printed the URL.
        try:
            webbrowser.open(ISSUES_URL)
        except Exception:
            pass  # the URL above is the source of truth


def main() -> None:
    """Entry point for the ``gzhseam`` console script."""
    cli()


if __name__ == "__main__":
    main()
