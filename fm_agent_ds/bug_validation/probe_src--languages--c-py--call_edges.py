"""Probe script for bug src--languages--c-py--call_edges.

Scenario: CodeGraph backend exists (from_proj_dir returns a valid extractor),
but C backend is unavailable (not in _CG_LANG). The spec requires returning None,
but the code calls cg.get_call_edges("c") unconditionally, returning a non-None value.
"""
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure the repo root is on the path so 'src' is importable.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)


def main():
    try:
        from src.languages.c import call_edges

        # Simulate: CodeGraph DB exists (from_proj_dir returns a mock extractor),
        # but get_call_edges("c") returns {} because "c" is not in _CG_LANG
        # (mirrors the actual _CG_LANG fallback: if not cg_langs → return {})
        mock_cg = MagicMock()
        mock_cg.get_call_edges.return_value = {}

        with patch(
            "src.languages.c.CodeGraphExtractor.from_proj_dir",
            return_value=mock_cg,
        ) as _mock_from:
            actual = call_edges("/fake/proj_dir")

        # Spec claim: "When the CodeGraph backend is unavailable for C, returns None."
        expected = None
        passed = actual != expected

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if passed:
        print(
            f"CONFIRMED — actual: {actual!r} | expected: {expected!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — actual matched expected: {actual!r}"
        )


if __name__ == "__main__":
    main()
