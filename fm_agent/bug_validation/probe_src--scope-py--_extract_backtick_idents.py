"""Probe script for bug src--scope-py--_extract_backtick_idents.

Bug: _extract_backtick_idents (called via _parse_issue_signals) strips
leading/trailing underscores from identifiers via .strip('_').

Trigger: input '`__init__`' → buggy code returns {'init'}, spec expects {'__init__'}.
"""
import sys
from pathlib import Path

# Ensure the project root is on sys.path so 'src' is importable
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from src.scope import _parse_issue_signals

    # The trigger condition: backtick-quoted __init__
    issue_text = "`__init__`"
    signals = _parse_issue_signals(issue_text)
    actual = signals["backtick_idents"]

    # Per spec, '__init__' should be preserved (not stripped to 'init')
    expected_wanted = "__init__"
    expected_unwanted = "init"

    # The bug strips underscores, so we expect 'init' in result but not '__init__'
    has_buggy = expected_unwanted in actual
    has_spec_correct = expected_wanted in actual

    # CONFIRMED = bug exists (stripped underscores, returns 'init' instead of '__init__')
    bug_reproduced = has_buggy and not has_spec_correct

    if bug_reproduced:
        print(f"CONFIRMED — actual: {actual!r} | expected '__init__' preserved, 'init' absent")
    elif has_spec_correct and not has_buggy:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
    else:
        print(f"NOT CONFIRMED — ambiguous: actual={actual!r}, expected='__init__' but got neither")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
