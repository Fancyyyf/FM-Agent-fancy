"""Probe script for bug dashboard-py--_llm_status_style."""
import sys
import os
import tempfile

result = "NOT CONFIRMED"

try:
    # Use a temp directory as probe workspace (FM-Agent self-validation guard)
    probe_tmp = tempfile.mkdtemp(prefix="probe_llm_status_style_")
    # Ensure repo root is on path for the package entry-point import
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # Import via public entry point: dashboard.py
    from dashboard import _llm_status_style

    # Bug trigger: code=0 (integer, non-None but falsy), status=None
    # Spec requires: text = str(code) = "0" since code is non-None
    # Buggy code: code or status or "?" -> 0 or None or "?" -> "?" because 0 is falsy
    actual = _llm_status_style(0, None)

    # Spec-correct: code=0 is non-None, so text="0", which is non-200, non-4xx, non-FMT -> color="red", label="0"
    expected = ("red", "0")

    if actual != expected:
        result = "CONFIRMED"
        print(f"CONFIRMED - actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED - actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
