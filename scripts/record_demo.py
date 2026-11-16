# ruff: noqa: E501 — injected card markup keeps CSS rules on single lines
"""Record the recruiter demo video from the live WASM dashboard.

Phases
------
probe    load the live URL once (warms the Pyodide cache) and dump the geometry
         the capture depends on, so a take never records a wrong frame
capture  render the four beat cards + end card, then record each app block with
         a CDP screencast (frames land in output/demo/frames/<block>/)

Why this file looks the way it does (all learned the hard way, 2026-11-16):
  * marimo renders `mo.ui.*` widgets INSIDE OPEN SHADOW ROOTS. `document.querySelectorAll`
    finds none of them; Playwright CSS locators pierce shadow boundaries, so every
    query below goes through locators.
  * the app scrolls an INNER DIV, not `window` — `window.scrollTo` is a no-op.
    The div is found once and animated from Python so the smoothness is real.
  * section 05 has no banner on the live build (its `mo.Html()` is not the cell's
    last expression), so the capture targets the slider itself, and the captions
    never say "section 05".

Usage (playwright is injected, never added to the project's dependencies):

    PYTHONUTF8=1 uv run --with playwright python scripts/record_demo.py probe
    PYTHONUTF8=1 uv run --with playwright python scripts/record_demo.py capture
    PYTHONUTF8=1 uv run --with playwright python scripts/build_demo_video.py
"""

from __future__ import annotations

import argparse
import base64
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from demo_timeline import BLOCKS, CARD_BODY, CARD_CSS  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "demo"
FRAMES = OUT / "frames"
CARDS = OUT / "cards"
PROFILE = OUT / "profile"
LIVE = "https://batestguy.github.io/dangote-refinery-optimizer/"
VIEW = {"width": 1600, "height": 900}
DSF = 1.2  # 1600x900 CSS @1.2 device scale -> native 1920x1080 rasters
BOOT_TIMEOUT_MS = 600_000

CURSOR_JS = """
() => {
  if (document.getElementById('__demo_cursor')) return;
  const s = document.createElement('style');
  s.textContent = `
    #__demo_cursor{position:fixed;left:0;top:0;width:26px;height:26px;border-radius:50%;
      background:rgba(255,255,255,.94);border:2px solid #171d64;
      box-shadow:0 2px 10px rgba(23,29,100,.45);z-index:2147483647;pointer-events:none;
      transform:translate(-50%,-50%) scale(var(--cs,1));transition:opacity .2s linear}
    .__rip{position:fixed;width:14px;height:14px;border-radius:50%;border:2px solid #f0513a;
      z-index:2147483646;pointer-events:none;animation:__rip .46s ease-out forwards}
    @keyframes __rip{from{transform:translate(-50%,-50%) scale(1);opacity:.95}
                     to{transform:translate(-50%,-50%) scale(5.2);opacity:0}}`;
  document.head.appendChild(s);
  const c = document.createElement('div');
  c.id = '__demo_cursor';
  document.body.appendChild(c);
  window.__demoCursorShow = v => { c.style.opacity = v ? '1' : '0'; };
  window.__demoCursorScale = v => { c.style.setProperty('--cs', String(1 / v)); };
  window.addEventListener('mousemove', e => {
    c.style.left = e.clientX + 'px';
    c.style.top = e.clientY + 'px';
  }, true);
  window.addEventListener('mousedown', e => {
    const r = document.createElement('div');
    r.className = '__rip';
    r.style.left = e.clientX + 'px';
    r.style.top = e.clientY + 'px';
    document.body.appendChild(r);
    setTimeout(() => r.remove(), 520);
  }, true);
}
"""

FIND_SCROLL_JS = """
() => {
  let best = null, bestScore = 0;
  const walk = root => {
    for (const el of root.querySelectorAll('*')) {
      if (el.scrollHeight > el.clientHeight + 40 && el.clientHeight > 300) {
        const score = el.scrollHeight - el.clientHeight;
        if (score > bestScore) { bestScore = score; best = el; }
      }
      if (el.shadowRoot) walk(el.shadowRoot);
    }
  };
  walk(document);
  if (best) { window.__demoScrollEl = best; }
  return best ? {scrollH: best.scrollHeight, clientH: best.clientHeight} : null;
}
"""


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def log(msg: str) -> None:
    print(f"[demo] {msg}", flush=True)


def pump(page, ms: float) -> None:
    """Wait while letting the sync API dispatch screencast frames."""
    page.wait_for_timeout(int(ms))


class Screencast:
    """CDP screencast -> timestamped JPEG frames (VFR), acked one by one."""

    def __init__(self, page, outdir: pathlib.Path):
        self.outdir = outdir
        self.outdir.mkdir(parents=True, exist_ok=True)
        self.frames: list[dict] = []
        self.cdp = page.context.new_cdp_session(page)
        self.cdp.on("Page.screencastFrame", self._on_frame)

    def _on_frame(self, params) -> None:
        # Ack FIRST: the browser withholds the next frame until acked, so writing
        # the JPEG before acking silently caps the capture rate (~12 fps measured).
        try:
            self.cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
        except Exception:  # noqa: BLE001
            pass
        idx = len(self.frames)
        path = self.outdir / f"{idx:05d}.jpg"
        try:
            path.write_bytes(base64.b64decode(params["data"]))
        except Exception as exc:  # noqa: BLE001 — never let a bad frame kill a take
            log(f"frame write failed: {exc}")
            return
        self.frames.append({"ts": params["metadata"].get("timestamp", 0.0), "path": str(path)})

    def start(self) -> None:
        self.cdp.send(
            "Page.startScreencast",
            {
                "format": "jpeg",
                "quality": 80,
                "maxWidth": 1920,
                "maxHeight": 1080,
                "everyNthFrame": 1,
            },
        )

    def stop(self) -> dict:
        try:
            self.cdp.send("Page.stopScreencast")
        except Exception:  # noqa: BLE001
            pass
        if len(self.frames) > 1:
            span = self.frames[-1]["ts"] - self.frames[0]["ts"]
            fps = len(self.frames) / span if span > 0 else 0.0
        else:
            fps = 0.0
        meta = {"frames": len(self.frames), "fps": round(fps, 2), "list": self.frames}
        (self.outdir / "frames.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
        log(f"  {self.outdir.name}: {len(self.frames)} frames @ {fps:.1f} fps")
        return {"frames": len(self.frames), "fps": round(fps, 2)}


def scroll_y(page) -> float:
    return page.evaluate("() => window.__demoScrollEl ? window.__demoScrollEl.scrollTop : 0")


def scroll_to(page, y: float, ms: int = 900) -> None:
    page.evaluate(
        """async ([y, ms]) => {
            const el = window.__demoScrollEl;
            if (!el) return;
            const start = el.scrollTop, dist = y - start, t0 = performance.now();
            await new Promise(res => {
              const step = now => {
                const p = Math.min(1, (now - t0) / ms);
                const e = p * p * (3 - 2 * p);
                el.scrollTop = start + dist * e;
                p < 1 ? requestAnimationFrame(step) : res();
              };
              requestAnimationFrame(step);
            });
          }""",
        [float(y), int(ms)],
    )


def box(loc) -> dict | None:
    try:
        b = loc.first.bounding_box()
    except Exception:  # noqa: BLE001
        return None
    if not b:
        return None
    return {
        "x": b["x"],
        "y": b["y"],
        "w": b["width"],
        "h": b["height"],
        "cx": b["x"] + b["width"] / 2,
        "cy": b["y"] + b["height"] / 2,
    }


def reveal(page, loc, offset: int = 140, ms: int = 900) -> dict | None:
    """Scroll the app's own container so `loc` sits `offset` px from the top."""
    b = box(loc)
    if b is None:
        return None
    scroll_to(page, max(0.0, scroll_y(page) + b["y"] - offset), ms)
    pump(page, ms + 150)
    return box(loc)


def camera(page, cx: float, cy: float, scale: float, ms: int = 700) -> None:
    """Punch-in/pan: translate+scale on <html>; cursor hidden while zoomed."""
    page.evaluate(
        """async ([cx, cy, s, ms]) => {
            const h = document.documentElement;
            const tx = innerWidth / 2 - cx * s;
            const ty = innerHeight / 2 - cy * s;
            h.style.transition = `transform ${ms}ms cubic-bezier(.4,0,.2,1)`;
            h.style.transformOrigin = '0 0';
            h.style.transform = `translate(${tx}px, ${ty}px) scale(${s})`;
            if (window.__demoCursorShow) window.__demoCursorShow(s === 1);
            if (window.__demoCursorScale) window.__demoCursorScale(s);
            await new Promise(r => setTimeout(r, ms + 40));
          }""",
        [float(cx), float(cy), float(scale), int(ms)],
    )
    pump(page, 130)


def reset_camera(page, ms: int = 700) -> None:
    page.evaluate(
        """async ([ms]) => {
            const h = document.documentElement;
            h.style.transition = `transform ${ms}ms cubic-bezier(.4,0,.2,1)`;
            h.style.transform = 'none';
            if (window.__demoCursorShow) window.__demoCursorShow(true);
            if (window.__demoCursorScale) window.__demoCursorScale(1);
            await new Promise(r => setTimeout(r, ms + 40));
          }""",
        [int(ms)],
    )
    pump(page, 130)


def chart(page, i: int):
    """The inner Plotly div (the <marimo-plotly> host itself is zero-size)."""
    return page.locator("marimo-plotly .js-plotly-plot").nth(i)


def slider_track(page):
    """Radix slider inside marimo-slider's shadow root — there is no input[type=range]."""
    return page.locator("marimo-slider [data-testid=track]")


def slider_thumb(page):
    return page.locator("marimo-slider [role=slider]")


def hover_bar(page, chart_idx: int, point_idx: int = 0) -> bool:
    """Hover a real Plotly bar so the real tooltip renders (locator pierces shadow)."""
    # NOT locator.hover(): Plotly overlays a `rect.nsewdrag` drag layer that
    # intercepts pointer events, so Playwright retries for seconds and gives up.
    # A real mouse move at the bar's centre still reaches Plotly's hover handler.
    try:
        pts = page.locator("marimo-plotly").nth(chart_idx).locator("g.point")
        count = pts.count()
        if count <= point_idx:
            log(f"  chart {chart_idx}: only {count} points")
            return False
        b = pts.nth(point_idx).bounding_box()
        if not b:
            log(f"  chart {chart_idx}: point {point_idx} has no box")
            return False
        page.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, steps=14)
        return True
    except Exception as exc:  # noqa: BLE001
        log(f"  hover failed: {type(exc).__name__}: {exc}")
        return False


# --------------------------------------------------------------------------- #
# page setup
# --------------------------------------------------------------------------- #
def open_browser(p):
    PROFILE.mkdir(parents=True, exist_ok=True)
    log(f"launching chromium, profile={PROFILE}")
    return p.chromium.launch_persistent_context(
        str(PROFILE),
        headless=True,
        viewport=VIEW,
        device_scale_factor=DSF,
        locale="en-NG",
        timezone_id="Africa/Lagos",
        timeout=120_000,
    )


def widgets(page) -> dict:
    """Count the widgets that only exist after Pyodide has executed their cells.

    marimo hosts `mo.ui.*` inside OPEN SHADOW ROOTS, so Playwright CSS locators are
    the only reliable query (plain `querySelectorAll` sees none of them). Counts,
    not visibility: a custom element can be a zero-size host and still be rendered.
    """
    return {
        "plotly": page.locator("marimo-plotly").count(),
        "slider": page.locator("marimo-slider").count(),
        "button": page.locator("marimo-button").count(),
        "banners": page.locator(".sec h2").count(),
        "kpis": page.locator(".kpi").count(),
    }


def load_dashboard(page, shot: pathlib.Path | None = None) -> float:
    t0 = time.time()
    log("browser up; navigating to live URL")
    page.goto(LIVE, wait_until="domcontentloaded", timeout=180_000)
    log(f"domcontentloaded at {time.time() - t0:.0f}s")
    deadline = t0 + BOOT_TIMEOUT_MS / 1000
    seen = {}
    while time.time() < deadline:
        seen = widgets(page)
        if (
            seen["plotly"] >= 3
            and seen["slider"] >= 1
            and seen["button"] >= 1
            and seen["banners"] >= 4
            and seen["kpis"] >= 5
        ):
            break
        pump(page, 1500)
        if int(time.time() - t0) % 30 < 2:
            log(f"  boot {time.time() - t0:.0f}s: {seen}")
    else:
        raise RuntimeError(f"dashboard never finished booting: {seen}")
    page.evaluate(FIND_SCROLL_JS)
    took = time.time() - t0
    log(f"dashboard ready in {took:.0f}s: {seen}")
    if shot:
        page.screenshot(path=str(shot))
    return took


# --------------------------------------------------------------------------- #
# probe
# --------------------------------------------------------------------------- #
def do_probe(page) -> dict:
    run = page.locator("marimo-button button").filter(has_text="Run")
    probe = {
        "url": LIVE,
        "viewport": VIEW,
        "device_scale_factor": DSF,
        "title": page.title(),
        "chips": page.evaluate(
            "() => [...document.querySelectorAll('.chip')].map(e => e.innerText.trim())"
        ),
        "kpis": page.evaluate(
            """() => [...document.querySelectorAll('.kpi')].map(e => ({
                 label: (e.querySelector('.label') || {}).innerText || '',
                 value: (e.querySelector('.value') || {}).innerText || ''}))"""
        ),
        "banners": page.evaluate(
            "() => [...document.querySelectorAll('.sec h2')].map(e => e.innerText.trim())"
        ),
        "counts": {
            "plotly": page.locator("marimo-plotly").count(),
            "points": page.locator("marimo-plotly g.point").count(),
            "slider": page.locator("marimo-slider input[type=range]").count(),
            "button": run.count(),
        },
        "run_button": box(run),
        "slider": box(page.locator("marimo-slider input[type=range]")),
        "charts": [
            box(page.locator("marimo-plotly").nth(i))
            for i in range(page.locator("marimo-plotly").count())
        ],
        "scroll": page.evaluate(FIND_SCROLL_JS),
    }
    (OUT / "probe.json").write_text(json.dumps(probe, indent=1), encoding="utf-8")
    page.evaluate("() => { if (window.__demoScrollEl) window.__demoScrollEl.scrollTop = 0; }")
    page.screenshot(path=str(OUT / "probe_view.png"))
    return probe


# --------------------------------------------------------------------------- #
# cards
# --------------------------------------------------------------------------- #
def render_cards(ctx) -> None:
    CARDS.mkdir(parents=True, exist_ok=True)
    for name in CARD_BODY:
        p2 = ctx.new_page()
        p2.set_viewport_size(VIEW)
        html = f"""<!doctype html><html><head><meta charset="utf-8">
        <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500&display=swap" rel="stylesheet">
        <style>{CARD_CSS}</style></head><body>{CARD_BODY[name]}</body></html>"""
        p2.set_content(html, wait_until="load")
        pump(p2, 1200)
        p2.screenshot(path=str(CARDS / f"{name}.png"))
        p2.close()
        log(f"card rendered: {name}")


# --------------------------------------------------------------------------- #
# block actions
# --------------------------------------------------------------------------- #
def act_hero(page) -> None:
    # Keep the frame moving for the whole slot: a static tail emits no screencast
    # frames and leaves the clip frozen for seconds (measured: 4.3 s of dead air).
    scroll_to(page, 0, 400)
    pump(page, 1600)
    page.mouse.move(770, 250, steps=18)
    pump(page, 500)
    scroll_to(page, 330, 4200)
    pump(page, 900)
    scroll_to(page, 690, 3800)
    page.mouse.move(1180, 430, steps=22)
    pump(page, 2200)


def act_kpi(page) -> None:
    grid = page.locator(".kpi-grid")
    reveal(page, grid, offset=110)
    pump(page, 1400)
    tiles = [box(page.locator(".kpi").nth(i)) for i in range(page.locator(".kpi").count())]
    tiles = [t for t in tiles if t]
    if tiles:
        camera(page, tiles[0]["cx"], tiles[0]["cy"], 1.45, 800)
        pump(page, 4200)
        if len(tiles) > 1:
            camera(page, tiles[1]["cx"], tiles[1]["cy"], 1.45, 900)
            pump(page, 3000)
        if len(tiles) > 3:
            camera(page, tiles[3]["cx"], tiles[3]["cy"], 1.45, 900)
            pump(page, 3400)
    reset_camera(page, 700)
    pump(page, 1100)


def rest_cursor(page) -> None:
    """Park the pointer in the left gutter so no Plotly tooltip fires."""
    page.mouse.move(150, 430, steps=18)
    page.mouse.move(190, 470, steps=10)


def act_s03(page) -> None:
    if reveal(page, page.locator(".duo"), offset=110) is None:
        log("  .duo not found")
    pump(page, 1700)
    # No hover here: these two traces ship Plotly's default template, so the
    # tooltip renders raw "x=100 y=Alaska North Slope text=100.0%" debug text.
    # The bars are already direct-labelled; park the cursor in the page gutter.
    reveal(page, chart(page, 0), offset=120)
    pump(page, 900)
    rest_cursor(page)
    pump(page, 3400)
    reveal(page, chart(page, 1), offset=120)
    pump(page, 800)
    rest_cursor(page)
    pump(page, 3400)
    if reveal(page, page.locator(".strip"), offset=150) is None:
        log("  photo strip not found")
    pump(page, 2300)


def act_s04(page) -> None:
    table = page.locator("table").filter(has_text="CVaR").first
    reveal(page, table, offset=170)
    pump(page, 1100)
    b = box(table)
    if b:
        camera(page, b["cx"], b["cy"], 1.5, 700)
        pump(page, 3100)
        reset_camera(page, 650)
        pump(page, 800)
    if reveal(page, page.locator(".figscroll"), offset=150) is None:
        log("  .figscroll not found")
    pump(page, 2300)
    reveal(page, chart(page, 2), offset=130)
    pump(page, 700)
    hover_bar(page, 2, 0)
    pump(page, 3300)


def act_run_a(page) -> None:
    track = slider_track(page)
    if reveal(page, track, offset=330) is None:
        log("  slider track not found")
    pump(page, 1200)
    tb, rb = box(slider_thumb(page)), box(track)
    if tb and rb:
        page.mouse.move(tb["cx"], tb["cy"], steps=16)
        pump(page, 300)
        page.mouse.down()
        pump(page, 240)
        page.mouse.move(rb["x"] + rb["w"] * 0.34, tb["cy"], steps=24)
        pump(page, 240)
        page.mouse.up()
        pump(page, 1500)
    else:
        log(f"  slider drag skipped (thumb={bool(tb)}, track={bool(rb)})")
    btn = page.locator("marimo-button button").filter(has_text="Run")
    bb = box(btn)
    if bb is None:
        log("  run button not found")
        return
    page.mouse.move(bb["cx"], bb["cy"], steps=18)
    pump(page, 550)
    page.mouse.click(bb["cx"], bb["cy"])
    pump(page, 1500)


def act_run_b(page) -> float:
    """Wait for the live result; returns the real seconds the solve took."""
    t0 = time.time()
    try:
        page.wait_for_function(
            """() => (document.body.innerText || '').includes('Deep re-optimization')""",
            timeout=300_000,
        )
    except Exception:  # noqa: BLE001
        log("  result card not seen within 300 s")
    took = time.time() - t0
    log(f"  live solve wait: {took:.1f}s")
    pump(page, 700)
    return took


def act_run_c(page) -> None:
    pump(page, 800)
    card = page.locator(".card").filter(has_text="Deep re-optimization").first
    b = box(card)
    if b:
        reveal(page, card, offset=120)
        pump(page, 600)
        b = box(card) or b
        camera(page, b["cx"], b["cy"], 1.35, 700)
        pump(page, 3900)
        reset_camera(page, 650)
        pump(page, 2200)
    else:
        log("  result card missing")
        pump(page, 7000)


ACTIONS = {
    "hero": act_hero,
    "kpi": act_kpi,
    "s03": act_s03,
    "s04": act_s04,
    "run_a": act_run_a,
    "run_b": act_run_b,
    "run_c": act_run_c,
}


# --------------------------------------------------------------------------- #
# phases
# --------------------------------------------------------------------------- #
def phase_probe() -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = open_browser(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        load_dashboard(page)
        probe = do_probe(page)
        log(json.dumps({k: probe[k] for k in ("counts", "scroll", "chips")}, indent=1))
        log(f"probe written: {OUT / 'probe.json'}")
        ctx.close()


def phase_capture(only: list[str] | None) -> None:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = open_browser(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        load_dashboard(page)
        page.evaluate(CURSOR_JS)
        render_cards(ctx)

        manifest_path = OUT / "record_manifest.json"
        manifest = {"blocks": {}, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                pass

        for blk in BLOCKS:
            if only and blk["id"] not in only:
                continue
            if blk["kind"] in ("card", "fade"):
                manifest["blocks"][blk["id"]] = {
                    "kind": blk["kind"],
                    "dur": blk["dur"],
                    "card": blk["card"],
                    "mode": "still",
                }
                continue
            log(f"block {blk['id']} ({blk['kind']}, {blk['dur']}s)")
            page.evaluate(CURSOR_JS)
            reset_camera(page, 250)
            sc = Screencast(page, FRAMES / blk["id"])
            sc.start()
            took = None
            try:
                res = ACTIONS[blk["kind"]](page)
                if isinstance(res, float):
                    took = res
            except Exception as exc:  # noqa: BLE001 — degrade, don't lose the take
                log(f"  action error: {type(exc).__name__}: {exc}")
            pump(page, 400)
            page.screenshot(path=str(FRAMES / blk["id"] / "still.png"))
            entry = {"kind": blk["kind"], "dur": blk["dur"], "mode": "screencast"}
            entry.update(sc.stop())
            if took is not None:
                entry["solve_wait_s"] = round(took, 1)
            if blk["kind"] == "run_c":
                m = re.search(r"Runtime:\s*([\d.]+)s", page.inner_text("body"))
                if m:
                    entry["runtime_text"] = m.group(1)
                    log(f"  solve runtime on screen: {m.group(1)}s")
            manifest["blocks"][blk["id"]] = entry
            manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")

        manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        ctx.close()
    log(f"capture done: {OUT}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["probe", "capture"])
    ap.add_argument("--blocks", default="", help="comma-separated block ids for capture")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    only = [b.strip() for b in args.blocks.split(",") if b.strip()]
    if args.phase == "probe":
        phase_probe()
    else:
        phase_capture(only or None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
