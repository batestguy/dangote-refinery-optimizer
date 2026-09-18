"""Free-tier driver notebook (marimo) — Phase 1 kickoff on Google Colab.

Open on Colab, or run locally:  uv run marimo edit notebooks/00_free_tier_driver.py
Pattern (docs/setup-steps.md step 8): clone → editable install → guarded probes →
commit only small derived artifacts, never raw dumps.

marimo rule honored here: every name is defined in exactly ONE cell
(same name in two cells = MultipleDefinitionError).
"""

import marimo

__generated_with = "0.12.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md(
        """
        # 00 · Free-tier driver
        Runs on **Colab free CPU**. Steps: clone repo → editable install →
        check EIA key → **stream** (not download) CrudeOilMix → peek Electric
        Sheep pricing → summarize. Raw data never gets committed.
        """
    )
    return


@app.cell
def _():
    import os
    import subprocess
    import sys
    from pathlib import Path

    IN_COLAB = "google.colab" in sys.modules or bool(os.environ.get("COLAB_RELEASE_TAG"))
    REPO_URL = "https://github.com/batestguy/dangote-refinery-optimizer.git"

    if IN_COLAB and not Path("dangote-refinery-optimizer").exists():
        subprocess.run(["git", "clone", "--depth", "1", REPO_URL], check=True)
        os.chdir("dangote-refinery-optimizer")
    if IN_COLAB:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-e", "."], check=True)
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "datasets"], check=False)
    except Exception:  # noqa: BLE001 — preinstalled on real Colab
        pass
    return (IN_COLAB,)


@app.cell
def _(IN_COLAB, mo, os):
    import getpass

    key = os.environ.get("EIA_API_KEY")
    if not key and IN_COLAB:
        key = getpass.getpass("EIA API key (input hidden, Enter to skip): ") or None
    mo.md(
        "✅ EIA key present"
        if key
        else "⚠️ No EIA key — register free at eia.gov/opendata (Phase 1 blocker)"
    )
    return (key,)


@app.cell
def _(mo):
    # Single cell for both dataset probes: `load_dataset` is defined exactly once
    # (marimo forbids redefining a name across cells). Failure of one probe must
    # not crash the other. `datasets` install happens in the env cell above.
    out = []
    try:
        from datasets import load_dataset

        ds = load_dataset("anon12-neurips-2026/CrudeOilMix", split="train", streaming=True)
        rows = list(ds.take(3))
        cols = list(rows[0].keys()) if rows else []
        shown = ", ".join(cols[:12])
        extra = " …" if len(cols) > 12 else ""
        out.append(f"✅ CrudeOilMix **streams** OK — columns: {shown}{extra}")
    except Exception as e:  # noqa: BLE001 — probes must never crash the notebook
        out.append(f"⚠️ CrudeOilMix streaming probe failed: `{e!r}`")

    try:
        from datasets import load_dataset as _ld  # same cell, alias is fine

        es = _ld(
            "electricsheepafrica/africa-synth-energy-oilgas-crude-pricing-nigeria",
            split="train",
            streaming=True,
        )
        peek = list(es.take(5))
        out.append(f"📄 Electric Sheep pricing ({len(peek)} rows peeked): {peek[:2]}")
    except Exception as e:  # noqa: BLE001
        out.append(f"⚠️ Electric Sheep peek failed: `{e!r}`")

    mo.md("\n\n".join(out))
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## Next
        - Phase 1 `src/dangote_opt/data/acquire.py` replaces these probes with
          cached, tested pulls (parquet → `data/raw/`, gitignored).
        - Commit **only** small derived artifacts; keep raw data in Colab Drive/local.
        """
    )
    return


if __name__ == "__main__":
    app.run()
