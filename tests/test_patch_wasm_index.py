"""The post-export WASM patch inserts its wait notice exactly once."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "patch_wasm_index",
    Path(__file__).resolve().parents[1] / "scripts" / "patch_wasm_index.py",
)
assert _SPEC is not None and _SPEC.loader is not None
patch_wasm_index = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(patch_wasm_index)

PAGE = '<html><body><div id="root"></div><script>x()</script>\n  </body>\n</html>\n'


def test_notice_inserted_before_body_close():
    out = patch_wasm_index.patch_html(PAGE)
    assert out.count(patch_wasm_index.MARKER) == 1
    assert "up to ~5 minutes" in out
    assert out.index("dangote-wait") < out.rindex("</body>")
    assert out.endswith("</script>\n</body>\n</html>\n")


def test_patch_is_idempotent():
    once = patch_wasm_index.patch_html(PAGE)
    assert patch_wasm_index.patch_html(once) == once


def test_missing_body_raises():
    with pytest.raises(ValueError):
        patch_wasm_index.patch_html("<html></html>")
