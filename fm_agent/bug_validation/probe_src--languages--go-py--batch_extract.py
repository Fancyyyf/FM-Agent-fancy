"""Probe script for bug: batch_extract does not catch exceptions from from_proj_dir.

Spec claim: Returns an empty dict when CodeGraph initialization fails.
Actual: If from_proj_dir raises, batch_extract propagates the exception.

Trigger: Pass an invalid type (None) as proj_dir to force os.path.join to raise TypeError
inside CodeGraphExtractor.from_proj_dir.
"""

import os
import sys

# Add repo root to Python path so `src.languages.go` is importable
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.languages.go import batch_extract

    # from_proj_dir calls os.path.join(proj_dir, ".codegraph", "codegraph.db")
    # Passing None forces os.path.join to raise TypeError
    result = batch_extract(None)
    # If we reach here, no exception was raised — the function handled it
    print(f"NOT CONFIRMED — batch_extract(None) returned: {result!r} (no exception raised)")
except TypeError as e:
    # Bug confirmed: exception propagated instead of returning {}
    print(f"CONFIRMED — batch_extract(None) raised TypeError instead of returning {{}}: {e}")
except Exception as e:
    # Any other exception propagating is also a violation
    print(f"CONFIRMED — batch_extract(None) raised {type(e).__name__} instead of returning {{}}: {e}")
