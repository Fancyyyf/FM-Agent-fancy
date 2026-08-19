"""Probe script for bug src--entry_reasoning_pipeline-py--_fqn_to_ident.

The bug: _fqn_to_ident at line 129 uses `hyphen > 0` which rejects
components like `-cpp` (where rfind("-") returns 0). For input
`src::-cpp::foo::bar`, the spec expects `foo::bar` but the code returns `bar`
because `-cpp` is not recognized as a source-file component.
"""

import sys
import os

# Add repo root to path so the import works
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.entry_reasoning_pipeline import _fqn_to_ident

    # Test case: input where the source-file component starts with a hyphen
    actual = _fqn_to_ident("src::-cpp::foo::bar")
    expected = "foo::bar"
    passed = actual != expected

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
