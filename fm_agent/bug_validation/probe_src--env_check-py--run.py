import sys
import os
import logging
import tempfile
import traceback

# Ensure the repo root is on sys.path so 'src' is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Capture logging.warning calls before importing the module
captured_warnings = []
_original_warning = logging.warning

def _capture_warning(msg, *args, **kwargs):
    if args:
        msg = msg % args
    captured_warnings.append(str(msg))

logging.warning = _capture_warning

try:
    from src.env_check import run

    class _FakeConfig:
        LLM_API_KEY = ""  # empty key triggers the LLM key check to fail

    tmpdir = tempfile.mkdtemp()
    result = run(tmpdir, _FakeConfig())

    logging.warning = _original_warning

    # Check for the bug: warning should be "[!] <label>: <message>" per spec,
    # but code produces "  [!] <label>: <message>" with two leading spaces
    bug_confirmed = False
    actual_msg = None
    for msg in captured_warnings:
        if msg.startswith("  [!]"):
            bug_confirmed = True
            actual_msg = msg
            break

    if bug_confirmed:
        print(f"CONFIRMED — warning format has leading spaces: {actual_msg!r} | expected: '[!] <label>: <message>'")
    else:
        print(f"NOT CONFIRMED — no warning with leading spaces found")
        print(f"Captured warnings: {captured_warnings!r}")

except Exception as e:
    logging.warning = _original_warning
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
