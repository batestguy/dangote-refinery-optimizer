#!/usr/bin/env bash
# Replicates the Colab free-tier workflow (docs/setup-steps.md step 8) on a Linux
# box/WSL: clone the public repo fresh → venv → pip-compatible editable install →
# package sanity → headless marimo export → pytest. No sudo, no system changes:
# uses a standalone uv binary staged under a scratch dir.
#
# Usage:  bash scripts/colab-wsl-test.sh
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRATCH="$ROOT/.colab-test"   # scratch only; gitignored
UV_DIR="$SCRATCH/uv-x86_64-unknown-linux-gnu"
REPO_URL="${REPO_URL:-https://github.com/batestguy/dangote-refinery-optimizer.git}"

mkdir -p "$SCRATCH" && cd "$SCRATCH" || exit 1

# stage standalone uv if missing
if [ ! -x "$UV_DIR/uv" ]; then
  echo "== staging standalone uv =="
  curl -sL -o uv.tar.gz https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz
  tar -xzf uv.tar.gz && rm uv.tar.gz
fi
UV="$UV_DIR/uv"
export UV_CACHE_DIR="$SCRATCH/.uvcache"
export UV_PYTHON_INSTALL_DIR="$SCRATCH/.uvpython"

rm -rf "$SCRATCH/repo" && mkdir -p "$SCRATCH/repo" && cd "$SCRATCH/repo" || exit 1

echo "== [1/5] clone public repo (Colab pattern) =="
git clone --depth 1 "$REPO_URL" . 2>&1 | tail -1

echo "== [2/5] environment =="
"$UV" venv --python 3.12 .venv 2>&1 | tail -2
# shellcheck disable=SC1091
source .venv/bin/activate
python --version

echo "== [3/5] editable install (Colab pattern: pip install -e .) =="
"$UV" pip install -q -e . && echo "install OK"
python -c "import dangote_opt; print('package OK, version', dangote_opt.__version__)" || exit 3

echo "== [4/5] objective sanity =="
python - <<'PY'
import numpy as np
from dangote_opt.optimization.objective import RefineryObjective, simplex_repair

o = RefineryObjective(
    np.array([33.5, 30.5, 33.8, 33.3, 31.7]),
    np.array([0.16, 0.24, 0.13, 2.9, 1.3]),
    np.array([78.0, 77.5, 78.5, 72.0, 68.0]),
    np.array([95.0, 100.0, 90.0, 70.0]),
)
print("equal-weight margin/bbl:", round(-o(np.r_[np.full(5, 0.2), 0.5]), 2))
print("simplex repair sums to:", round(simplex_repair(np.array([2, 1, 1, 0, 0.0])).sum(), 6))
PY
[ $? -eq 0 ] || exit 4

echo "== [5/5] headless marimo export of Colab driver (structure check) =="
PYTHONUTF8=1 python -m marimo export script notebooks/00_free_tier_driver.py > driver_out.md 2> driver_err.log \
  && echo "DRIVER OK" || { echo "DRIVER FAILED:"; tail -20 driver_err.log; exit 5; }

echo "== [bonus] full test suite on Linux =="
"$UV" pip install -q pytest && python -m pytest -q 2>&1 | tail -2

echo "== COLAB-TEST COMPLETE (scratch: $SCRATCH) =="
