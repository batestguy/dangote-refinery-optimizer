# HF Space push runbook — Step 18 item 2 (user actions)

Everything mechanical is done: `scripts/build_space_root.py` assembles the
exact directory to push, runs the deploy-safety assertions (no `.env`, no
`*.pkl`, marimo CVE floor + lock-drift guards), and generates the Space
`README.md` with the Docker frontmatter. The assembly was **verified by
Space simulation** — `marimo export html` run inside `deploy/space_root/`
with the local package uninstalled, i.e. exactly what the Space image will
execute. What's left is account + push — about 10 minutes.

## 1. Create the Space (one-time, web UI)

1. Log in at huggingface.co → **New Space**.
2. Space name: `dangote-blend-optimizer` (or your pick — used in the URLs below).
3. SDK: **Docker** → Blank template. License: MIT. Visibility: Public.
4. Create. (An empty Space repo appears; we push over it in step 3.)

## 2. Assemble the Space root (every deploy)

```bash
PYTHONUTF8=1 uv run python scripts/build_space_root.py
```

The script hard-fails on: pin drift between `deploy/requirements.txt` and
`uv.lock`, marimo below the 0.23.0 CVE floor, missing derived artifacts, any
`.env` or `*.pkl` in the tree. Output: `deploy/space_root/`.

## 3. Push (first time: full setup; afterwards: 3 commands)

**One-time setup** — create a token at huggingface.co/settings/tokens
(scope: **write**), then:

```bash
git remote add hf https://huggingface.co/YOUR_HF_USERNAME/dangote-blend-optimizer
```

**Every deploy:**

```bash
PYTHONUTF8=1 uv run python scripts/build_space_root.py
cd deploy/space_root
git init -b main && git add -A && git commit -m "deploy: dashboard build"
git remote add hf https://huggingface.co/YOUR_HF_USERNAME/dangote-blend-optimizer
git push hf main --force
```

(`--force` is correct here: the Space root is a generated build artifact and
its history is disposable; the real history lives in the GitHub repo.)

Alternative without git-in-the-folder: the Space web UI → **Files** →
**Add file → Upload files** — drag the *contents* of `deploy/space_root/`.

## 4. Verify (the acceptance gate)

1. Watch the Space build log (first build installs pinned wheels, ~2 min).
2. Open the app → the full static story (KPI strip, ticker, charts, risk
   figures) renders from committed artifacts.
3. **Cold-start gate:** after the Space sleeps (~48 h), reopen it — the
   static story must render **< 2 s**; the KPI footnote reads "bridge" (the
   Space never ships the pkl) and the deep re-opt completes in ~1 s.
4. Ticker: FX shows 🟢 live; WTI shows 🔵 snapshot unless you add
   `EIA_API_KEY` in Space settings → Variables and secrets (optional, free).
5. **No-secrets check (do once after the first push):** the Space **Files**
   tab must show no `.env` — only what `build_space_root.py` staged.

## 5. Update the GitHub README badge

Add to `README.md` (replace YOUR_HF_USERNAME):

```markdown
[![Space](https://img.shields.io/badge/🤗%20Space-live-blue)](https://huggingface.co/spaces/YOUR_HF_USERNAME/dangote-blend-optimizer)
```
