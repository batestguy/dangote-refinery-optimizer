"""Assemble the Hugging Face Space root — Phase 6 (setup-steps Step 18, item 2).

Copies the app and its runtime dependencies into ``deploy/space_root/`` — the
exact directory tree to push to the Space repository (the Space root IS the
image root for a Docker Space). Runs the deploy-safety assertions first so a
bad tree can never ship:

* no ``.env`` (EIA key) anywhere in the assembled tree;
* no ``models/*.pkl`` (the app must take the bridge path — verified);
* committed derived artifacts present (cold-start story layer);
* Space ``requirements.txt`` pins match ``uv.lock`` (drift guard);
* pin-floor guard: marimo >= 0.23.0 (CVE-2026-39987).

Idempotent: safe to re-run after every change; the generated tree is
gitignored (it is a build artifact, not source).
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPACE_ROOT = ROOT / "deploy" / "space_root"
MARIMO_FLOOR = (0, 23, 0)

# Runtime deps the app actually imports (plus plotly for the charts). joblib
# arrives with scikit-learn; matplotlib is training-time only.
REQUIRED_PINS = (
    "marimo",
    "numpy",
    "pandas",
    "pyarrow",
    "scipy",
    "scikit-learn",
    "python-dotenv",
    "requests",
    "plotly",
)

# data/derived slices the app reads at import time (the cold-start story layer).
DERIVED_FILES = (
    "slate_phase1.parquet",
    "prices_phase2.parquet",
    "prices_phase2.json",
    "costs_phase2.parquet",
    "costs_phase2.json",
    "scenarios_phase5.json",
    "sensitivity_phase4.json",
    "ticker_latest.json",
)


def check_pin_floor(lock_text: str) -> None:
    """Assert the locked marimo satisfies the CVE floor (fail loudly otherwise)."""
    match = re.search(r'name = "marimo"\nversion = "([^"]+)"', lock_text)
    if not match:
        raise RuntimeError("uv.lock: marimo entry not found")
    version = tuple(int(p) for p in match.group(1).split(".")[:3])
    if version < MARIMO_FLOOR:
        raise RuntimeError(f"uv.lock marimo {match.group(1)} is below the CVE floor {MARIMO_FLOOR}")


def check_requirements_match_lock(lock_text: str) -> None:
    """Every REQUIRED_PINS must exist in uv.lock at the version we pin."""
    for pkg in REQUIRED_PINS:
        match = re.search(rf'name = "{re.escape(pkg)}"\nversion = "([^"]+)"', lock_text)
        if not match:
            raise RuntimeError(f"uv.lock has no entry for required pin {pkg!r}")


def check_no_secrets(dest: Path) -> None:
    """Deploy-safety: no .env files anywhere in the assembled tree."""
    for env_file in dest.rglob(".env"):
        raise RuntimeError(f"ASSEMBLED TREE CONTAINS {env_file} — never ship secrets")


def check_no_models(dest: Path) -> None:
    """Deploy-safety: no pkl artifacts (bridge path is the Space contract)."""
    for pkl in dest.rglob("*.pkl"):
        raise RuntimeError(f"ASSEMBLED TREE CONTAINS {pkl} — the Space runs the bridge path")


def copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".pytest_cache", ".ruff_cache", "*.egg-info"
        ),
    )


def assemble() -> Path:
    lock_text = (ROOT / "uv.lock").read_text(encoding="utf-8")
    check_pin_floor(lock_text)
    check_requirements_match_lock(lock_text)

    requirements = (ROOT / "deploy" / "requirements.txt").read_text(encoding="utf-8")
    pinned = dict(line.split("==") for line in requirements.splitlines() if "==" in line)
    missing = [p for p in REQUIRED_PINS if p not in pinned]
    if missing:
        raise RuntimeError(f"deploy/requirements.txt missing pins: {missing}")
    for pkg in REQUIRED_PINS:
        match = re.search(rf'name = "{re.escape(pkg)}"\nversion = "([^"]+)"', lock_text)
        locked = match.group(1)
        if pinned[pkg] != locked:
            raise RuntimeError(
                f"pin drift: {pkg} requirements={pinned[pkg]} vs uv.lock={locked} "
                "(re-derive deploy/requirements.txt from uv.lock)"
            )

    if SPACE_ROOT.exists():
        shutil.rmtree(SPACE_ROOT)
    SPACE_ROOT.mkdir(parents=True)

    # 1. The app at root (the Dockerfile CMD runs app.py).
    shutil.copy2(ROOT / "app" / "app.py", SPACE_ROOT / "app.py")

    # 2. The package (the app imports dangote_opt from src/).
    copy_tree(ROOT / "src" / "dangote_opt", SPACE_ROOT / "src" / "dangote_opt")

    # 3. Committed derived artifacts — the cold-start story layer.
    derived = SPACE_ROOT / "data" / "derived"
    derived.mkdir(parents=True)
    for name in DERIVED_FILES:
        src = ROOT / "data" / "derived" / name
        if not src.exists():
            raise RuntimeError(f"missing required derived artifact: {name}")
        shutil.copy2(src, derived / name)

    # 4. Risk figures + credited photos the dashboard renders (the hero photo
    # is embedded in app.py as a data URI — the source file must ship with it).
    assets = SPACE_ROOT / "docs" / "assets"
    assets.mkdir(parents=True)
    for name in ("margin_fan.png", "tornado_margin.png"):
        src = ROOT / "docs" / "assets" / name
        if not src.exists():
            raise RuntimeError(f"missing required figure: {name}")
        shutil.copy2(src, assets / name)
    credited = assets / "credited"
    credited.mkdir(parents=True)
    for name in (
        "refinery_site_hero.jpg",
        "cdu_unit.jpg",
        "procedures_a.jpg",
        "procedures_b.jpg",
        "procedures_c.jpg",
        "CREDITS.md",
    ):
        src = ROOT / "docs" / "assets" / "credited" / name
        if not src.exists():
            raise RuntimeError(f"missing required credited asset: {name}")
        shutil.copy2(src, credited / name)

    # 5. Deploy files at root: requirements.txt, Dockerfile, Space README
    #    (the frontmatter SDK: docker is what makes HF build it as a Docker Space).
    shutil.copy2(ROOT / "deploy" / "requirements.txt", SPACE_ROOT / "requirements.txt")
    shutil.copy2(ROOT / "deploy" / "Dockerfile", SPACE_ROOT / "Dockerfile")
    shutil.copy2(ROOT / "deploy" / "space_readme.md", SPACE_ROOT / "README.md")

    # Safety assertions on the finished tree.
    check_no_secrets(SPACE_ROOT)
    check_no_models(SPACE_ROOT)

    return SPACE_ROOT


def main() -> int:
    dest = assemble()
    file_count = sum(1 for p in dest.rglob("*") if p.is_file())
    print(f"Space root assembled: {dest}")
    print(f"  {file_count} files")
    print("  safety: no .env, no *.pkl, pin floors + lock drift verified")
    print("  next: push this directory to your HF Space repo (deploy/hf-push-runbook.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
