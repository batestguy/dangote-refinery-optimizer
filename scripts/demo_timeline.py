# ruff: noqa: E501 — card markup/CSS is written as one line per property on purpose
"""Single source of truth for the demo video (see demo-video-spec.md).

Blocks, durations, caption lines and beat-card copy live here so the recorder
and the assembler can never drift apart. Times are video-time seconds.
"""

LIVE_URL = "batestguy.github.io/dangote-refinery-optimizer"
REPO_URL = "github.com/batestguy/dangote-refinery-optimizer"
AUTHOR = "JJMB"

# id, kind, duration. Sum == 150.0 s (spec §5).
BLOCKS = [
    {"id": "b01", "kind": "card", "card": "problem", "dur": 15.0},
    {"id": "b02", "kind": "hero", "dur": 15.0},
    {"id": "b03", "kind": "kpi", "dur": 16.0},
    {"id": "b04", "kind": "card", "card": "method", "dur": 14.0},
    {"id": "b05", "kind": "s03", "dur": 18.0},
    {"id": "b06", "kind": "s04", "dur": 14.0},
    {"id": "b07", "kind": "card", "card": "stakes", "dur": 10.0},
    {"id": "b08a", "kind": "run_a", "dur": 8.0},
    {"id": "b08b", "kind": "run_b", "dur": 6.0},  # real wait, compressed on assembly
    {"id": "b08c", "kind": "run_c", "dur": 8.0},
    {"id": "b09", "kind": "card", "card": "takeaway", "dur": 10.0},
    {"id": "b10", "kind": "card", "card": "end", "dur": 12.0},
    {"id": "b11", "kind": "fade", "card": "end", "dur": 4.0},
]

# Captions: block id -> list of (offset_in_block, duration, text). First person,
# per spec D15. Numbers match what the live build renders (140 offline tests);
# a stale "137" string survives in origin/gh-pages:index.html but is not shown.
CAPTIONS = {
    "b01": [
        (0.2, 4.6, "I built an optimizer for a 650,000 barrel-a-day refinery."),
        (5.0, 4.8, "At that scale, $1 per barrel of margin is about $237 million a year."),
        (
            10.0,
            4.8,
            "The decision: which of five crudes, in what blend, at what cracking severity.",
        ),
    ],
    "b02": [
        (
            0.5,
            7.0,
            "This is the console. Five real published assays, EIA prices, quality specs enforced.",
        ),
        (8.0, 6.5, "First visit downloads Python in your browser — this starts after it loads."),
    ],
    "b03": [
        (
            0.2,
            5.4,
            "At base prices the optimum is ~100% Alaska North Slope at maximum severity: $15.67 a barrel.",
        ),
        (
            6.0,
            5.4,
            "Eleven percent above a naive equal-weight blend — and it matches the exact LP optimum to under half a cent.",
        ),
        (11.6, 4.2, "Re-optimizing as prices move is worth another $2.56 a barrel."),
    ],
    "b04": [
        (0.2, 4.4, "Assays → TBP cut-point bridge → four product yields."),
        (
            4.8,
            4.6,
            "Extra Trees learn that physics; differential evolution searches it; an exact LP checks the answer.",
        ),
        (9.6, 4.2, "Then 10,000 price scenarios — and 140 tests pass offline in CI."),
    ],
    "b05": [
        (0.2, 5.4, "Section 03: what it chose — and how often that choice changes."),
        (
            5.8,
            6.2,
            "Across 10,000 price worlds Alaska North Slope wins half the time; Forcados takes most of the rest.",
        ),
        (12.2, 5.6, "So the diet isn't a fixed answer. It's a rule that depends on crack spreads."),
    ],
    "b06": [
        (0.2, 4.2, "Section 04 is the part most demos skip: risk."),
        (4.6, 5.4, "Re-optimizing every scenario turns the worst 5% tail from −$3.50 to +$1.42."),
        (10.2, 3.6, "Only 0.8% of price worlds lose money."),
    ],
    "b07": [
        (0.2, 4.6, "Flexibility isn't just margin. It's downside protection."),
        (
            5.0,
            4.8,
            "And because the physics are affine, the answer is provable — not just plausible.",
        ),
    ],
    "b08a": [
        (0.2, 3.6, "At the bottom, I set the baseline severity, then press Run."),
        (4.2, 3.4, "This is a real click — the solver runs in the browser."),
    ],
    "b08b": [
        (
            0.3,
            5.4,
            "Differential evolution searches the diet and the severity, then checks itself against the exact LP.",
        ),
    ],
    "b08c": [
        (0.3, 3.9, "DE and LP land on the same margin. That's the honest bar."),
        (4.4, 3.3, "Solve time printed on screen — inside the 30-second budget."),
    ],
    "b09": [
        (
            0.5,
            8.6,
            "ML surrogate, global optimization, live deployment — and the discipline to publish where it's weak.",
        ),
    ],
    "b10": [
        (0.4, 3.8, "Live demo: batestguy.github.io/dangote-refinery-optimizer"),
        (4.4, 4.6, "Code and full methodology: github.com/batestguy/dangote-refinery-optimizer"),
        (9.4, 2.2, "Project by JJMB · 2026"),
    ],
    "b11": [],
}

CARD_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1600px;height:900px;background:#171d64;overflow:hidden}
body{font-family:'Barlow Condensed','Arial Narrow','Segoe UI',sans-serif;color:#fff}
.rule{position:absolute;top:0;left:0;right:0;height:8px;background:#f0513a}
.wrap{position:absolute;inset:0;padding:88px 108px 250px 108px;display:flex;
      flex-direction:column;justify-content:center}
.eyebrow{font-family:'IBM Plex Mono',Consolas,monospace;font-size:19px;letter-spacing:.24em;
         color:#ff8d7a;text-transform:uppercase;margin-bottom:24px}
h1{font-size:88px;line-height:.97;text-transform:uppercase;letter-spacing:.01em;max-width:20ch}
h1 em{color:#ff8d7a;font-style:normal}
.big{font-family:'IBM Plex Mono',Consolas,monospace;font-size:42px;margin-top:24px;color:#fff}
.sub{margin-top:26px;font-family:'IBM Plex Sans','Segoe UI',sans-serif;font-size:23px;
     line-height:1.45;color:#cdd2f2;max-width:46ch}
.stages{display:flex;gap:10px;flex-wrap:wrap;margin-top:26px;align-items:center}
.stage{border:1px solid rgba(240,81,58,.8);background:rgba(240,81,58,.16);border-radius:999px;
       padding:9px 16px;font-family:'IBM Plex Mono',Consolas,monospace;font-size:16px;letter-spacing:.05em}
.arrow{color:#ff8d7a;font-size:18px}
ul{margin-top:22px;list-style:none}
li{font-family:'IBM Plex Sans','Segoe UI',sans-serif;font-size:24px;line-height:1.45;
   color:#dfe3ff;margin-bottom:12px}
li b{color:#fff}
.foot{position:absolute;left:108px;bottom:64px;font-family:'IBM Plex Mono',Consolas,monospace;
      font-size:16px;color:#8f96cf;letter-spacing:.12em;text-transform:uppercase}
.url{font-family:'IBM Plex Mono',Consolas,monospace;font-size:34px;margin-top:6px;color:#fff}
"""

CARD_BODY = {
    "problem": """
<div class="rule"></div><div class="wrap">
  <div class="eyebrow">The problem</div>
  <h1>650,000 <em>barrels</em> a day</h1>
  <div class="big">$1/bbl of margin ≈ $237M a year</div>
  <div class="sub">Which five crudes, in what blend, at what cracking severity?
  Chosen on paper — and a wrong answer costs money every single day.</div>
</div>
<div class="foot">Crude blend optimizer · 650 kbpd</div>
""",
    "method": """
<div class="rule"></div><div class="wrap">
  <div class="eyebrow">What I built</div>
  <h1>Five assays. Four yields. One <em>provable</em> optimum.</h1>
  <div class="stages">
    <span class="stage">REAL ASSAYS</span><span class="arrow">→</span>
    <span class="stage">TBP BRIDGE</span><span class="arrow">→</span>
    <span class="stage">4 PRODUCT YIELDS</span><span class="arrow">→</span>
    <span class="stage">ETR SURROGATE</span><span class="arrow">→</span>
    <span class="stage">DE + EXACT LP</span><span class="arrow">→</span>
    <span class="stage">10,000 SCENARIOS</span>
  </div>
  <div class="sub">Physics first. Machine learning on top. An exact linear program
  as the referee — so the optimizer cannot flatter itself.</div>
</div>
<div class="foot">Assays → bridge → surrogate → DE → risk</div>
""",
    "stakes": """
<div class="rule"></div><div class="wrap">
  <div class="eyebrow">Why it matters</div>
  <h1>Flexibility is <em>downside protection</em></h1>
  <div class="big">worst-5% tail: −$3.50 → +$1.42 /bbl</div>
  <div class="sub">Re-optimizing per scenario does not just add margin — it turns the
  loss tail positive. And because the physics are affine, the optimum is provable,
  not just plausible.</div>
</div>
<div class="foot">10,000 bootstrapped price worlds</div>
""",
    "takeaway": """
<div class="rule"></div><div class="wrap">
  <div class="eyebrow">What this proves</div>
  <h1>ML + OR + deployment, <em>end to end</em></h1>
  <ul>
    <li><b>Surrogate</b> — R² ≥ 0.982, dual CV, weak spots published</li>
    <li><b>Optimizer</b> — DE meets the exact LP to &lt;$0.005/bbl</li>
    <li><b>Deployment</b> — runs in the browser, no server to wake</li>
    <li><b>Audit trail</b> — every number cited or labelled ASSUMED</li>
  </ul>
</div>
<div class="foot">Project by JJMB · 2026</div>
""",
    "end": """
<div class="rule"></div><div class="wrap">
  <div class="eyebrow">Live demo</div>
  <div class="url">batestguy.github.io/dangote-refinery-optimizer</div>
  <div class="eyebrow" style="margin-top:34px">Code + full methodology</div>
  <div class="url">github.com/batestguy/dangote-refinery-optimizer</div>
  <div class="foot">Project by JJMB · 2026</div>
</div>
""",
}
