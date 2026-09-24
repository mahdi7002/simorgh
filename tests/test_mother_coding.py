from __future__ import annotations

from core.mother.coding import _extract_patch, _validate_patch_paths


def test_patch_paths_are_repo_relative():
    patch = """diff --git a/core/x.py b/core/x.py
--- a/core/x.py
+++ b/core/x.py
@@ -1 +1 @@
-old
+new
"""
    assert _validate_patch_paths(patch) == ["core/x.py"]
    extracted = _extract_patch("~~~diff\n" + patch + "\n~~~")
    assert extracted == patch


def test_patch_paths_reject_traversal():
    bad = """diff --git a/core/x.py b/../outside.py
--- a/core/x.py
+++ b/../outside.py
"""
    try:
        _validate_patch_paths(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe patch path accepted")
