# examples/wash_a_deck.md — a 3-line "this is what using it looks like"

```bash
gzhseam wash my-deck.html -o gzh-ready.html        # m1: local wash (no network)
gzhseam wash my-deck.html -o gzh-ready.html --cdn   # m2: also re-host <img> on 公众号 CDN (stub at m1)
gzhseam wash my-deck.html -o gzh-ready.html -v      # verbose: print every tag/attr/font rewrite
```

Then open the 公众号 editor, paste `gzh-ready.html` in, and edit a single character in
place — no agent re-run, no manual HTML surgery, no platform strip-on-paste.
