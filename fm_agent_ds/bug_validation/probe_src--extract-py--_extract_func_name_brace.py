"""Probe for bug: _extract_func_name_brace matches operator pattern
inside angle brackets before stripping them, producing a false match.

Bug ID: src--extract-py--_extract_func_name_brace
"""

import sys
import os
from pathlib import Path

# Ensure the repo root is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from src.extract import _extract_func_name_brace

    # Minimal lang_cfg with no keywords (none needed for the test)
    lang_cfg: dict = {"keywords": set()}

    # Signature text where `operator()(int)` appears inside angle brackets.
    # The real function name is `bar`, but `re.search` will match
    # `operator()` inside the template parameter list first because
    # angle brackets are NOT stripped before the operator-pattern scan.
    signature_text: str = "void bar(Template<operator()(int)> t)"

    actual: str | None = _extract_func_name_brace(signature_text, lang_cfg)
    expected: str = "bar"

    # The bug is CONFIRMED if actual != expected (the operator inside <>
    # was matched instead of the real function name).
    passed: bool = actual != expected

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
