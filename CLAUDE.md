# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

The import above is the canonical orientation (commands, data→decision
architecture, conventions, settled decisions, gotchas). This file adds only what
`AGENTS.md` does not cover. Where the two disagree on project *state* (phase,
test count), trust the top `★ HANDOFF` block in `knowledge.md`, which is updated
every session. `AGENTS.md` lags: Phase 6 is code-complete and Phase 7 has started.

## Start of session

Read the top `★ HANDOFF` section of `knowledge.md` first. It holds the live
next-session queue and any **OPEN THREAD** to resume.

## Running a subset of tests

```bash
uv run pytest tests/test_bridge.py                          # one file
uv run pytest tests/test_objective.py::test_simplex_repair_normalizes   # one test
uv run pytest -k batch                                      # by keyword
```

CI (`.github/workflows/ci.yml`) runs only `uv sync` → `ruff check .` →
`pytest` on Python 3.12. `ruff format` and `marimo check` are local-only, so
run them yourself.

## Package layout

Source is `src/dangote_opt/` (hatch wheel, editable install via `uv sync`).
`config.py` holds every locked constant: specs, penalties, DE budget. Change
numbers there, not inline, and cite them in `docs/methodology.md`.

## One app, three deploy surfaces

`app/app.py` is a single marimo notebook that must work in all three:

1. **Local / HF Docker Space.** `scripts/build_space_root.py` assembles
   `deploy/space_root/` (gitignored build artifact) and asserts deploy safety:
   no `.env`, no `models/*.pkl`, derived artifacts present, requirements pinned
   to `uv.lock`, marimo ≥ 0.23.0. The Space sets `PYTHONPATH=/app/src` because
   it never pip-installs the package. Regenerate `deploy/requirements.txt` from
   `uv.lock` only, never from `uv pip list` (recipe in `deploy/README.md`).
2. **GitHub Pages (WASM / Pyodide).** Built with `marimo export html-wasm`. The
   package ships as a wheel in `app/public/wheels/`, and data and images live
   under `app/public/`. In WASM, file reads go through
   `pyodide.http.open_url(f"{mo.notebook_location()}/public/...")`, not local
   paths (see the helpers around `app/app.py:666`). Any new file the app reads
   needs both code paths **and** a copy under `app/public/`. The full rebuild
   and deploy recipe is in `knowledge.md` (deploy via a clean temp clone of
   `gh-pages`).
3. **Cold start.** Every live fetch (EIA, FX/WTI ticker) must have a
   committed-artifact fallback in `data/derived/`, and the app must not require
   the surrogate pkl: it falls back to the bridge path.

## marimo run-button "Failed to update value"

This is skew protection (a stale browser tab after a server restart), not a code
bug. Hard-refresh the tab first. Check the server log for the "invalid server
token" line before you change any code.
