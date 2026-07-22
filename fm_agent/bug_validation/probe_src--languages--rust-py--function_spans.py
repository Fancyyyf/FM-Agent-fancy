"""Probe: Confirm that function_spans returns methods in addition to top-level functions.

The spec (src/languages/rust.py [SPEC] block) states that function_spans returns
"one per top-level function declared in the file". However, the implementation
delegates to CodeGraphExtractor.get_function_spans, which queries for both
'function' AND 'method' kinds from the codegraph database. Methods inside impl
blocks should be excluded per the spec but are included in practice.

This probe mocks CodeGraphExtractor to return a mixed list and verifies that
methods leak through.
"""
import sys
import os

# Ensure the project root is on sys.path so 'src' imports resolve.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _run_probe():
    from unittest.mock import MagicMock, patch

    # Simulate a Rust file with:
    #   fn top_level() {}       -- top-level function at lines 1-3 (0-indexed: 0-2)
    #   impl Foo { fn bar() {} } -- method inside impl at lines 5-7 (0-indexed: 4-6)
    mock_spans = [
        ("top_level", 0, 2),
        ("Foo::bar", 4, 6),
    ]

    mock_cg = MagicMock()
    mock_cg.get_function_spans.return_value = mock_spans

    with patch("src.languages.rust.CodeGraphExtractor") as mock_cls:
        mock_cls.from_proj_dir.return_value = mock_cg

        from src.languages.rust import function_spans

        result = function_spans("/fake/proj", "/fake/proj/src/lib.rs")

    if result is None:
        return (
            "ERROR",
            "function_spans returned None — expected at least the mocked spans",
        )

    names = [name for name, _, _ in result]

    has_top_level = "top_level" in names
    has_method = "Foo::bar" in names

    # Per spec: only top-level function declarations should be returned.
    # If a method leaked through, the bug is confirmed.
    if has_method:
        return (
            "CONFIRMED",
            "function_spans returned method 'Foo::bar' (inside an impl block) "
            f"in addition to top-level function 'top_level'. "
            f"Spec requires only top-level functions. Full result: {result!r}",
        )
    elif has_top_level and not has_method:
        return (
            "NOT CONFIRMED",
            f"function_spans correctly filtered to only top-level functions: {result!r}",
        )
    else:
        return (
            "NOT CONFIRMED",
            f"Unexpected result (no top-level function found): {result!r}",
        )


if __name__ == "__main__":
    try:
        status, msg = _run_probe()
        print(f"{status} — {msg}")
        if status == "ERROR":
            sys.exit(1)
    except Exception as exc:
        print(f"ERROR — unhandled exception: {exc}")
        sys.exit(1)
