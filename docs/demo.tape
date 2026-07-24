# docs/demo.tape — vhs script for the 10-minute happy path.
# Render to assets/demo.gif via:
#   vhs docs/demo.tape    # local (needs vhs + ttyd + ffmpeg installed)
# Or via the .github/workflows/demo.yml workflow_dispatch job.
# The committed assets/demo.gif is the source of truth (the workflow only refreshes it on demand).

Output assets/demo.gif
Set FontSize 13
Set Width 1000
Set Height 460
Set Padding 16
Set Theme {"background": "#1D1D1F", "foreground": "#F5F5F7", "prompt": "#4DA3FF", "detail": "#A1A1A8", "title": "#8985FF", "success": "#2DC79A", "error": "#FF6B6B", "warning": "#FFB454"}

Hide
Type "pip install -e ."
Enter
Sleep 3s
Show

Type "# 1. wash a coding-agent HTML deck into 公众号-pasteable HTML (m1, local-only)"
Enter
Sleep 500ms

Type "gzhseam wash tests/fixtures/sample_deck.html -o gzh-ready.html --verbose"
Enter
Sleep 1s

Sleep 4s

Type "# 2. open the washed HTML — pure fragment, no <script>/<canvas>/on*, fonts in 公众号 allowed set"
Enter
Sleep 500ms

Type "head -n 12 gzh-ready.html"
Enter
Sleep 1s

Sleep 3s

Type "# 3. paste gzh-ready.html into the 公众号 editor → render → edit one word in place → publish"
Enter
Sleep 500ms

Type "# (m2 will add: --cdn re-hosts <img src> on the 公众号 CDN; m3 wires init + auth)"
Enter
Sleep 2s
