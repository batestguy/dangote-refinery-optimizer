# Demo Video — Crude Blend Optimizer (`demo-video-spec.md`)

**Status:** spec only — no code changed, no video recorded yet.
**Owner:** JJMB · **Date:** 2026-11-16
**Deliverable:** a recruiter-facing screen-capture demo of the live dashboard at
`https://batestguy.github.io/dangote-refinery-optimizer/`, cut to 2:30, scored
to "Odeal — Blur" starting at 0:55 and looped, with burned-in captions that
state the problem, what was achieved, and why it matters.

---

## 1. Why this exists

The project's Phase 7 deliverable list (`idea.txt` §Phase 7) calls for a
walkthrough video. The repo already has `docs/executive-summary.md`,
`docs/blog-post.md`, a 4-page brief PDF, and a live WASM demo — but nothing
that shows a human *driving* the app. A recruiter gives a portfolio ~30–60 s;
a silent, captioned screen recording with a clear problem → proof → stakes arc
is the artifact that survives that budget.

**Audience, in order:** (1) recruiters/HR skimming a LinkedIn or CV link,
(2) ML/OR hiring managers checking whether the numbers are real, (3) the
project owner as a reusable asset after UI changes.

**What the video must leave behind, in one sentence:**
> "This person took a real industrial decision, built the ML surrogate and the
> optimizer, deployed it live, and can prove the answer is optimal."

---

## 2. Context gathered before writing this spec

| Fact | Value | Source |
|---|---|---|
| App | marimo `App(width="medium")`, 1121 lines, deployed as WASM/Pyodide | `app/app.py` |
| Live URL | `https://batestguy.github.io/dangote-refinery-optimizer/` (HTTP 200, 167 KB `index.html`) | curl, 2026-11-16 |
| Live build | gh-pages commit `d6496e9` (2026-09-25) — one commit behind `main` (`d0e5b7d`) | `git log origin/gh-pages` |
| Sections | hero → 01 headline tiles → 02 market tape → 03 optimizer's choice → 04 risk → 05 run-it-yourself → 06 provenance accordions → footer | `app/app.py` |
| Real interactions | severity slider (0–1, step .01), `⚡ Run deep optimization` button, spinner, result card, 3 Plotly charts with hover tooltips, 3 accordions, external links | `app/app.py` L916–1110 |
| Audio | `Odeal - Blur (Official Lyric Video) - Odeal.mp3`, **121.128 s** total | ffprobe |
| Audio usable | 0:55 → end = **66.128 s** per loop | ffprobe |
| Tooling present | ffmpeg 9.0.2 w/ libx264, libass (`subtitles`/`ass`), `drawtext`, `loudnorm`; Node 24; Playwright 1.65 + Chromium cached in `~/AppData/Local/ms-playwright/b` | shell probe |
| Not present | `playwright` Python package in `.venv` (invoke via `uv run --with playwright`) | `.venv` probe |
| Headline numbers | $15.67/bbl optimum · +10.0% vs equal weight · +$2.56/bbl from re-optimizing · VaR5 $6.25 · CVaR5 $1.42 · P(loss) 0.8% · R² ≥ 0.982 · 140 offline tests · DE ≡ LP < $0.005 | README / `knowledge.md` |
| Scale fact | 650,000 bbl/day → $1/bbl = $650k/day ≈ **$237M/year** | arithmetic, stated in caption |

**Critical technical finding:** the deployed WASM build has no
`models/etr_surrogate.pkl` (gitignored by design), so the live app's
"Surrogate quality" tile renders **"bridge"**, not `0.982`, and the live Run
follows the exact bridge path. Captions therefore must **not point at a tile
that shows R²** — the model-quality claim is made on a beat card ("validated
R² ≥ 0.982, dual CV in the model card"), not by a zoom into the dashboard.
~~Test count caveat~~ **Resolved 2026-11-16:** the deployed build renders
`140 OFFLINE TESTS` in its hero chip (verified by loading the live page in
headless Chromium and reading the rendered DOM). A grep of
`origin/gh-pages:index.html` had found a stale `137` string inside the bundle,
but that is not what a visitor sees. **The video says 140** — it matches both
the frames and the README.

---

## 3. Locked decisions (from the interview)

| # | Decision | Choice |
|---|---|---|
| D1 | Format | **16:9, 1920×1080 only**, no vertical/square cutdown |
| D2 | Runtime | **~2:30 (150 s)**, ≈ 3 music passes |
| D3 | Narration | **Captions only.** Music is the only audio; no voiceover, no TTS |
| D4 | Music | **Loop 0:55→end continuously**, fade out at the close. **No ducking** (nothing to duck under — the "duck under narration" answer is superseded by D3; recorded here so it is not re-litigated) |
| D5 | Capture source | **The live GitHub Pages URL**, not local `marimo run` |
| D6 | Cold boot | **Jump-cut past it**; the 2–5 min first-visit wait lives in a caption on the hero |
| D7 | Story shape | **Hybrid:** 4 full-screen beat cards + captioned app footage between them |
| D8 | Pointer | **Real-looking cursor + click ripple + punch-in zoom** on the key numbers |
| D9 | Coverage | **Deep on 03–05**; ticker (02) and provenance accordions (06) cut from the main edit |
| D10 | Loop seams | **~1 s crossfade** at each loop point |
| D11 | Solver wait | **Speed-ramp the real solve** (capture real, compress in the edit) with a "live solve · N s" caption |
| D12 | Honesty | **Lead with strong numbers only** in the main cut; weak spots stay in the repo/model card |
| D13 | Deliverables | **MP4 + `.srt` sidecar** (no thumbnail, no music-free twin, no copy block) |
| D14 | Repo fit | **Committed recorder script**, MP4 kept in gitignored `output/` |
| D15 | Caption voice | **First person** ("I built…", "I chose…") |
| D16 | Opening framing | **Money first** — the refinery buys the wrong barrel by default |
| D17 | Capture width | **1600×900 viewport** (text ~1.2× larger than a 1920 capture) |
| D18 | Persistent chrome | **None** — no progress bar/watermark; beat cards only |
| D19 | End card | Live URL + repo + **"Project by JJMB"**; no email/LinkedIn |
| D20 | MP4 in git | **After the owner reviews and approves the cut** — then commit the MP4 and add a download link. Not before |

### 3.1 Coverage reconciliation ("all clicks and features" vs D9)

The original request asked for *all* clicks/features; D9 narrows the main cut
to fit 2:30. Resolution: the main cut shows every **decision-critical**
interaction, and the two omitted surfaces are named in a single caption line so
the video is not falsely exhaustive. An optional 3:00 extended cut is listed as
a post-approval extra (§12).

| Feature | Main cut | Notes |
|---|---|---|
| Hero + trust chips + 3-step stepper | ✅ on screen 0:15–0:30 | no click |
| 01 KPI tiles (5) | ✅ zoom, 0:30–0:46 | no click |
| 02 ticker + LIVE/STALE/SNAP badges | ❌ caption only | "context-only feed, display-only, never enters the optimizer" |
| 03 diet bar chart + hover tooltip | ✅ 1:00–1:18 | hover is a real interaction |
| 03 switch-share chart + hover | ✅ 1:00–1:18 | the two-regime finding |
| 03 photo strip + credits | ✅ ~3 s inside 03 | physical context |
| 04 risk table | ✅ zoom 1:18–1:32 | |
| 04 margin fan (PNG, `.figscroll`) | ✅ brief | sideways scroll on mobile, static on desktop |
| 04 tornado hover | ✅ | real hover |
| 05 severity slider drag | ✅ 1:42–2:04 | real click/drag |
| 05 Run button + spinner | ✅ | real click |
| 05 result table / baselines / LP callout | ✅ zoom | the money frame |
| 06 accordions A/B/C | ❌ extended cut only | |
| Footer provenance/links | ⚠️ 2 s at end, no click | links are not followed in-video |

---

## 4. Story architecture

Four typographic beat cards carry the argument; the app provides evidence
between them. Cards are full-frame, navy `#171D64` field with the flare-red
`#F0513A` top rule (the app's own design system, so the video looks like the
product), Barlow Condensed for headlines if available, otherwise Segoe UI
Black; mono numerals (Consolas) for every figure.

```
CARD 1  PROBLEM      the money
   ↓    app hero + 01 headline tiles   (evidence: what the machine says)
CARD 2  METHOD       5 real assays → bridge → ETR → DE → LP → 10k scenarios
   ↓    03 what it chose → 04 risk      (evidence: the answer and its tail)
CARD 3  STAKES       flexibility as downside protection; provable, not plausible
   ↓    05 live run                     (evidence: it actually executes)
CARD 4  TAKEAWAY     what this proves about the builder
   ↓    END CARD      live URL · repo · Project by JJMB
```

---

## 5. Timeline (exactly 150.0 s)

Times are video-time. Block boundaries are also the edit points; no camera
move is allowed across a music seam (§7.2).

| # | Start | Dur | Block | Content | Caption lines |
|---|---|---|---|---|---|
| 1 | 0:00 | 15 | **CARD 1 — Problem** | "650,000 barrels a day" / "$1/bbl ≈ $237M/year" / "which 5 crudes, what blend, what severity" | 3 |
| 2 | 0:15 | 15 | App hero | hero + 5 chips + stepper; slow scroll 0 → 120 px | 2 |
| 3 | 0:30 | 16 | 01 Headline tiles | punch-in 1.5× on tile 1 ($15.67), pan to uplift (+10.0%), re-opt (+$2.56), risk tile | 3 |
| 4 | 0:46 | 14 | **CARD 2 — Method** | pipeline line with 5 arrow-separated stages + "140 offline tests" (matches the live chip) | 3 |
| 5 | 1:00 | 18 | 03 Optimizer's choice | diet bar (hover Alaska North Slope), switch-share bar (hover Forcados), photo strip | 3 |
| 6 | 1:18 | 14 | 04 Risk | punch-in on VaR/CVaR rows, fan chart, tornado hover | 3 |
| 7 | 1:32 | 10 | **CARD 3 — Stakes** | "flexibility is downside protection" / "provable, not plausible" | 2 |
| 8 | 1:42 | 22 | 05 Run it yourself | drag slider 0.50 → 0.35, release; click Run; spinner (speed-ramped); result card; punch-in on DE vs LP rows | 4 |
| 9 | 2:04 | 10 | **CARD 4 — Takeaway** | "surrogate + optimizer + deployment + published weak spots" | 1–2 |
| 10 | 2:14 | 12 | End card | live URL, repo, "Project by JJMB · 2026" | 3 |
| 11 | 2:26 | 4 | Fade | hold end card, music fades to silence, fade to paper-white | 0 |

**Total: 150 s.** Caption budget ≈ 25 lines / ≈ 240–280 words ≈ 1.7 words/s,
inside comfortable reading speed for a feed.

---

## 6. Shot list (implementation-level)

All selectors are verified at capture time and written to
`output/demo/manifest.json`; if a selector fails the take aborts rather than
recording a wrong frame.

| Block | Camera | Actions | Assertions before the frame |
|---|---|---|---|
| 2 | none; scroll y 0 → 120 @ 60 px/s | none | `.hero h1` contains "Crude Blend"; 5 `.chip` elements present |
| 3 | punch-in 1.5× @ tile 1, then pan right | none | `.kpi-grid .kpi` count == 5; first tile text contains `$15.67` |
| 5 | none, then punch-in 1.4× on the red bar | hover diet bar → tooltip; hover Forcados bar → tooltip | both `.js-plotly-plot` present; tooltip text matches crude name |
| 6 | punch-in 1.6× on risk table rows 3–5 | hover tornado gasoline bar | table rows ≥ 8; tornado `<rect>` bars ≥ 8 |
| 8 | punch-in 1.6× on the two baseline rows | drag slider, click Run, wait for result card | button enabled; result card contains "DE margin" and "LP optimum"; `Runtime` string captured |
| 9/10 | none | none | live URL string typed from the manifest, never hand-typed |

**Cursor:** an injected DOM element (`#__demo_cursor`, 28 px, white fill, 2 px
navy outline, soft shadow) that follows every `page.mouse.move`, plus a 40 px
expanding ripple (300 ms) on `mousedown`. Because it lives in the page, the
screencast captures it natively — no OS cursor, no compositing, and it survives
headless capture.

**Scrolling:** never `mouse.wheel`. Drive `window.scrollTo` in `requestAnimationFrame`
steps over a fixed duration with an ease-in-out curve, so scroll speed is
reproducible and never stalls on a slow frame.

**Zoom:** a single `punch(x, y, scale, ms)` helper animating
`html { transform-origin: x y; transform: scale(s) }` with a 600 ms
cubic-bezier(.4,0,.2,1). Base capture is 1600×900, so a 1.6× punch renders
~1.6× of CSS pixels at 1.2 device scale — text is unambiguously legible.

**Cold boot (D6):** the recorder navigates, waits until `⚡ Run deep optimization`
exists, then quits and re-launches the persistent profile so the take starts on
a cached load. The hero caption reads:
`"First visit downloads Python in your browser (up to ~5 min). This starts after it loads."`
No boot footage is recorded.

---

## 7. Audio plan

### 7.1 The loop

- Source: `Odeal - Blur (Official Lyric Video) - Odeal.mp3`, 121.128 s.
- Segment: `[55.000 → 121.128]` = **66.128 s**.
- Three passes needed for 150 s; with 1 s crossfades the effective period
  becomes 65.128 s.
- Build: `seg.wav` → three copies → `acrossfade=d=1` chain → `atrim=0:150` →
  `afade=out:st=147:d=3`.
- Loudness: `loudnorm=I=-14:TP=-1:LRA=11` (YouTube/streaming reference), then a
  linear gain pass so the result is exactly -14 LUFS integrated. **No ducking
  (D4).** No compression beyond loudnorm.
- Result: seams land at ≈ **65.1 s** and ≈ **130.3 s** (verified by measuring
  the assembled wav, not assumed).

### 7.2 Seam masking (D10)

- 1 s crossfade at each seam.
- Extra insurance: freeze camera movement for ±1 s around each seam
  (64.0–66.2 and 129.2–131.4) so the softened jump coincides with stillness.
  Seam 1 lands inside block 5 (03, hovering the Forcados bar) and seam 2 inside
  block 9 (Card 4, static) — both are already low-motion, which is why this
  order of sections was chosen.

### 7.3 Why no voice

D3 (captions only) means the track *is* the audio bed; it must not be mixed as
background music with dips that make no sense without a voice. Constant level,
fade in over 0.6 s at 0:00, fade out 2:26→2:29, silence to 2:30.

**Copyright:** the track is a commercial release; YouTube/LinkedIn may
auto-claim or region-block it. That risk was raised and accepted knowingly
(D4). The `.srt` and the committed script make a music-free re-render a
one-command job if a claim ever bites — but no music-free twin is produced now
(D13).

---

## 8. Capture pipeline (live URL, D5)

**Runtime:** `uv run --with playwright --with pillow scripts/record_demo.py`
— do **not** add playwright to `pyproject.toml` production deps; the demo tool
is opt-in via `--with` so `uv sync` on the Space stays lean.

**Browser:** Chromium from the existing `ms-playwright` cache, headless
(`--headless=new`), viewport **1600×900**, `deviceScaleFactor: 1.2` → native
**1920×1080** rasters, `reducedMotion: "no-preference"`, fixed locale/timezone,
persistent user-data dir under `output/demo/profile` so the second take is warm.

**Frame capture:** CDP `Page.startScreencast` (`format=jpeg`, `quality=90`,
`maxWidth/maxHeight` 1920×1080), acknowledging every frame with its timestamp
and writing `frames/000123.jpg` + a `frames.jsonl` of `{ts, path}`. Assemble
VFR → `fps=60` CFR with ffmpeg. Rationale: Playwright's built-in
`record_video` is 25 fps and would judder on scrolling; gdigrab needs a visible
desktop and is not reproducible.

**Fallbacks, in order:** (1) `page.video` at 25 fps if the screencast drops
frames; (2) headful Chromium + `ffmpeg -f gdigrab` region capture as a last
resort, accepting that it is not reproducible.

**Takes:** capture **block by block** (11 clips), not one 150 s take. Each clip
starts from a fresh `page.goto` on the warm profile and runs at most ~25 s, so
a bad frame costs 3 s of work, not the whole video. CDP frame timestamps give
per-clip in/out points; clips are trimmed to the timeline table, then concat.

**Network discipline:** the app's ticker does live FX/WTI fetches. Accept
whatever badge (`LIVE`/`STALE`/`SNAP`) appears — section 02 is cut from the main
edit anyway. If offline, the app still renders from committed artifacts; the
take is still valid.

**Never on camera:** `.env`, the EIA key, terminal windows, the browser URL bar,
any file under `data/raw/`, or `output/playwright/*` debug artifacts.

---

## 9. Assembly

```
output/demo/
  clips/            # per-block webm/jpg frames
  frames/           # screencast frames (temporary, deleted after assembly)
  captions.json     # single source of truth for both .ass and .srt
  captions.ass      # burned-in (libass, 1920x1080)
  demo.srt          # sidecar
  demo_v1.mp4       # review cut
  manifest.json     # live build sha, capture timestamps, resolved selectors, per-block durations, solver runtime string
```

**Video encode:** `libx264 -preset slow -crf 18 -pix_fmt yuv420p -r 60
-movflags +faststart -profile:v high -level 4.2`.

**Captions:** one JSON (`{start, end, text, line2?}`) renders both `.ass` and
`.srt`, so they can never drift. `.ass` style: bottom-centre, `MarginV=64`,
`Fontsize=34` at 1080p, 2-line max, ≤ 44 chars/line, white on `#171D6466`
rounded band, key figures in `#F0513A`. Font: Segoe UI Semibold (guaranteed on
this box) with mono numerals; if a Barlow/IBM Plex TTF is fetched, pass
`fontsdir` so libass does not silently substitute.

**Fades/transitions:** hard cuts between app blocks (clean for UI), 200 ms
cross-dissolve into and out of beat cards, 1 s fade to `#f7f8fc` at 2:29.

**Chapters (optional, free):** because blocks are timed, emit a YouTube-chapter
list from the same manifest.

---

## 10. Caption script (first person, D15)

Draft text; final numbers must be replaced with the **values visible on the
captured frames** (see §2 caveat) before the `.ass` is rendered.

**Block 1 — Card 1 (Problem)**
1. "I built an optimizer for a 650,000 barrel-a-day refinery."
2. "At that scale, $1 per barrel of margin is about $237 million a year."
3. "The decision: which of five crudes, in what blend, at what cracking severity."

**Block 2 — Hero**
4. "This is the console. Five real published assays, EIA prices, quality specs enforced."
5. "First visit downloads Python in your browser — this starts after it loads."

**Block 3 — 01 Headline tiles**
6. "At base prices the optimum is ~100% Alaska North Slope at maximum severity: $15.67 a barrel."
7. "Ten percent above a naive equal-weight blend — and it matches the exact LP optimum to under half a cent."
8. "Re-optimizing as prices move is worth another $2.56 a barrel."

**Block 4 — Card 2 (Method)**
9. "Assays → TBP cut-point bridge → four product yields."
10. "Extra Trees learn that physics; differential evolution searches it; an exact LP checks the answer."
11. "Then 10,000 bootstrapped price scenarios, re-optimized one by one. 140 tests pass offline in CI."

**Block 5 — 03 Optimizer's choice**
12. "Section 03: what it chose — and how often that choice changes."
13. "Across 10,000 price worlds Alaska North Slope wins half the time; Forcados takes most of the rest."
14. "So the diet isn't a fixed answer. It's a rule that depends on crack spreads."

**Block 6 — 04 Risk**
15. "Section 04 is the part most demos skip: risk."
16. "Re-optimizing every scenario turns the worst 5% tail from −$3.50 to +$1.42."
17. "Only 0.8% of price worlds lose money."

**Block 7 — Card 3 (Stakes)**
18. "Flexibility isn't just margin. It's downside protection."
19. "And because the physics are affine, the answer is provable — not just plausible."

**Block 8 — 05 Run it yourself**
20. "Section 05 runs it live. I set the baseline severity, then press Run."
21. "Differential evolution picks the diet and the severity, then checks itself against the exact LP."
22. "DE and LP land on the same margin. That's the honest bar."
23. "Solve time printed on screen — inside the 30-second budget."

**Block 9 — Card 4 (Takeaway)**
24. "ML surrogate, global optimization, live deployment — and the discipline to publish where it's weak."

**Block 10 — End card**
25. "Live demo: batestguy.github.io/dangote-refinery-optimizer"
26. "Code and full methodology: github.com/batestguy/dangote-refinery-optimizer"
27. "Project by JJMB · 2026"

> Lines 6–8, 13, 16–17, 22 must be checked against the frames. If the live build
> prints different values (bridge path, stale test count, stale prices), the
> caption follows the frame, never the README.

---

## 11. Acceptance criteria

- [ ] Duration 150.0 ± 0.5 s; 1920×1080; 60 fps CFR; H.264 High, `yuv420p`, `+faststart`.
- [ ] Audio: single music bed starting on 0:55 of the track, looped, −14 LUFS integrated, true peak ≤ −1 dBTP, fades out 2:26→2:29, silence at the end. **No voice.**
- [ ] Two loop seams are inaudible on a laptop speaker at normal volume (spot-check 64–67 s and 129–132 s).
- [ ] All 27 caption lines are burned in, 2 lines max, inside the lower safe area, and never cover a number they describe.
- [ ] `.srt` sidecar matches the burned-in text and timings exactly.
- [ ] Every number spoken on screen appears on the captured frame; no caption contradicts a visible value.
- [ ] Real slider drag and real Run click are visible, including the click ripple; the solve is visibly real (spinner) before the result.
- [ ] Punch-ins land on the intended element in ≥ 95% of frames (no half-cropped number, no cut through a table header).
- [ ] No secrets, no terminal, no URL bar, no `.env`, no gitignored artifact on screen.
- [ ] End card links are character-perfect against `git remote -v` and the live URL.
- [ ] `ffprobe` output pasted into `manifest.json`; `scripts/record_demo.py` re-runs end to end without manual steps.
- [ ] Reviewer (owner) has watched the cut and approved before the MP4 is committed (D20).

---

## 12. Post-approval actions (explicitly gated)

1. **Owner reviews `output/demo/demo_v1.mp4`.** No commit of the video before this.
2. On approval: commit the MP4 (compressed, target ≤ 20 MB) plus `demo.srt` and
   `scripts/record_demo.py` + this spec; add a README download link and a poster
   frame. That is the "add mp4 to git and a download link" instruction — it
   happens **after** the review, not as part of the first pass.
3. Optional, only if asked: 3:00 extended cut that adds section 02 (ticker) and
   the three provenance accordions, restoring literal "all features" coverage.
4. Optional, only if asked: music-free twin for platforms that auto-claim.

---

## 13. Risks and fallbacks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Pyodide cold boot 2–5 min on a cold profile | High | Wastes a take | Warm persistent profile; cap the wait at 8 min then abort loudly; never record boot |
| Live build's hero chip vs README test count | **Resolved** | — | Live page renders `140 OFFLINE TESTS`; a stale `137` string exists only inside the bundle. Video says 140 |
| Surrogate tile shows "bridge" on the live build | Certain | Can't point at R² | Model-quality claim lives on Card 2 + model card, not a zoom |
| CDP screencast drops frames under load | Medium | Judder | Per-block capture; 90-quality JPEG; `fps=60` conform; fallback to `page.video` |
| Live solve is slow inside Pyodide (>30 s) | Medium | Eats the block | Speed-ramp compresses it; worst case the block is extended by trimming Block 5 by 4 s |
| Fonts absent for libass | Medium | Ugly substitution | Segoe UI Semibold/Consolas, verified with a single test frame before assembly |
| Music Content ID claim | Medium | Video muted/blocked | Accepted; one-command music-free re-render available |
| Windows console UTF-8 mangling in scripts | Low | Aborted run | `PYTHONUTF8=1`, ASCII-only log strings, check exit codes — never trust `tail -1` |
| Punch-in blurs text | Low | Legibility | `deviceScaleFactor: 1.2` (native 1080p raster) + bicubic zoom; verify a still before the full run |

---

## 14. Out of scope

- No changes to `app/app.py`, no UI fixes, no new dashboard features.
- No redeploy of the WASM build (that would be a gh-pages push, separately approved).
- No vertical/square cutdown, no thumbnail, no music-free export, no LinkedIn copy block (all declined in D1/D13).
- No voiceover recording; no narration track for later replacement.
- No analytics/UTM links in the end card.
