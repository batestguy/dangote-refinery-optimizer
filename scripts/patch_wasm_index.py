"""Add a first-visit wait notice to the exported WASM page (GitHub Pages).

Run after ``marimo export html-wasm``. Most of a first visit (several minutes on
slow or mobile connections) happens before any notebook cell runs: the browser
is still downloading Pyodide and the scientific Python stack behind marimo's
generic "Loading marimo..." spinner. The bootstrap cell's own callout in
``app/app.py`` only appears near the end of that wait. This script injects a
small static notice into ``index.html`` that shows from the first paint, counts
elapsed time, and removes itself as soon as the first cell output renders.

Idempotent: re-running on an already patched page changes nothing.

    uv run python scripts/patch_wasm_index.py output/wasm_vN
"""

from __future__ import annotations

import sys
from pathlib import Path

MARKER = "<!-- dangote-wait-notice -->"

NOTICE = (
    MARKER
    + """
<style>
  #dangote-wait {
    position: fixed; left: 16px; right: 16px; bottom: 56px; z-index: 2147483000;
    max-width: 520px; margin: 0 auto; padding: 14px 16px; border-radius: 10px;
    background: #171d64; color: #fff; border-top: 4px solid #f0513a;
    font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    box-shadow: 0 6px 24px rgba(23, 29, 100, 0.25);
  }
  #dangote-wait b { font-weight: 600; }
  #dangote-wait .dw-time { opacity: 0.75; font-variant-numeric: tabular-nums; }
</style>
<div id="dangote-wait" role="status" aria-live="polite">
  <b>Setting up the optimizer in your browser.</b> The first visit downloads a
  full scientific Python stack and can take <b>up to ~5 minutes</b> (longer on
  mobile data). Keep this tab open; later visits are faster.
  <div class="dw-time">Elapsed: <span id="dangote-wait-t">0:00</span></div>
</div>
<script>
  (function () {
    var box = document.getElementById("dangote-wait");
    var t = document.getElementById("dangote-wait-t");
    var t0 = Date.now();
    var timer = setInterval(function () {
      // Gone as soon as any cell output has rendered (the app's own
      // bootstrap callout takes over from there).
      var outs = document.querySelectorAll('[id^="output-"]');
      var shown = Array.prototype.some.call(outs, function (el) {
        return el.innerText.trim() !== "";
      });
      if (shown) {
        clearInterval(timer);
        box.remove();
        return;
      }
      var s = Math.floor((Date.now() - t0) / 1000);
      t.textContent = Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
    }, 1000);
  })();
</script>
"""
)


def patch_html(html: str) -> str:
    """Return ``html`` with the wait notice inserted before the last ``</body>``."""
    if MARKER in html:
        return html
    head, sep, tail = html.rpartition("</body>")
    if not sep:
        raise ValueError("no </body> in exported index.html")
    return head + NOTICE + sep + tail


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    index = Path(argv[1]) / "index.html"
    html = index.read_text(encoding="utf-8")
    patched = patch_html(html)
    if patched == html:
        print(f"{index}: already patched")
    else:
        index.write_text(patched, encoding="utf-8", newline="\n")
        print(f"{index}: wait notice added")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
