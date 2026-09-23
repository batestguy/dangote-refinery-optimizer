# HF Space deployment kit — Phase 6 (setup-steps Step 18, item 2)

Everything the Hugging Face Space needs on top of the repo root. The Space is
a **Docker Space** (official marimo template pattern): repo root = image root,
`app.py` at root, port 7860, non-root user.

## What ships (and what never does)

| Ships | Never ships (gitignored / secrets) |
|---|---|
| `app.py` (copy of `app/app.py`) | `.env` (EIA key — never) |
| `src/dangote_opt/**` | `data/raw/**` (EIA caches — regenerated live) |
| `data/derived/**` (slate, prices, costs, scenarios, ticker snapshot) | `models/*.pkl` (app falls back to the bridge path) |
| `requirements.txt`, `Dockerfile`, `README.md` | `.colab-test/`, notebooks, tests, CI |

The app is built for this: every live fetch has a committed-artifact fallback
(slate/prices/costs sidecars, Phase 5 precomputed summary, ticker snapshot), so
the Space renders precomputed content instantly on cold start (~48 h sleep)
and the deep re-opt stays a bridge-path run (~0.85 s, no surrogate needed).

## Files in this directory (copy to repo root of the Space)

* `requirements.txt` — exact versions from `uv.lock` (regenerate with the
  grep command below after any `uv sync`). `joblib`, `matplotlib`, `plotly`,
  `requests` arrive as transitive deps of the pinned set.
* `Dockerfile` — verbatim mirror of the official
  `marimo-team/marimo-app-template` Dockerfile (uv install, non-root user,
  `marimo run app.py --include-code --host 0.0.0.0 --port 7860`).

## Deploy checklist (user actions in **bold**)

1. **Create the Space**: huggingface.co → New Space → SDK: **Docker** →
   Blank template. Name suggestion: `dangote-blend-optimizer`.
2. Push the assembled root: `app.py` + `src/` + `data/derived/` +
   `requirements.txt` + `Dockerfile` (via git remote `hf` or the web uploader).
3. Watch the build log — first build installs the pinned wheels (~2 min).
4. **Cold-start acceptance**: after the Space sleeps, open it — precomputed
   content (slate table, Phase 5 summary, ticker snapshot badges) must render
   **< 2 s**; the deep re-opt button runs the bridge-path DE (~1 s + startup).
5. Ticker on the Space: FX is keyless and will show 🟢 live; WTI shows 🔵
   snapshot unless an `EIA_API_KEY` secret is added (Space settings →
   Variables and secrets — optional, free key).
6. **Verify no secrets in the pushed tree**: `git ls-files | grep -i env` must
   show only `.env.example`; sidecars carry no key (acquire.py contract).

## Regenerating requirements.txt from uv.lock

```bash
grep -A1 '^name = "marimo"' uv.lock   # + numpy/pandas/pyarrow/scipy/
# scikit-learn/python-dotenv — keep in sync with `uv pip list`
```

## Regenerating the ticker snapshot before each deploy

```bash
PYTHONUTF8=1 uv run python scripts/refresh_ticker_snapshot.py
git add data/derived/ticker_latest.json && git commit  # snapshot = cold-start fallback
```
