"""Probe script for bug ID: src--languages--erlang-py--_function_id

Tests that _function_id properly validates:
1. Arity must be a non-negative integer (label="foo/-1" should raise ValueError)
2. Label must be a string (label=42 should raise ValueError, not AttributeError)
"""
import os
import sys

# Ensure the repository root is on the Python path
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# FM-Agent self-validation: import the smallest relevant unit directly.
# _function_id is a pure function with no FM-Agent workflow dependencies.
from src.languages.erlang import _function_id

results = []

# --- Bug 1: Negative arity ---
# Spec: raises ValueError when arity is not a non-negative integer
# Code: int('-1') succeeds, so returns a string instead of raising
try:
    result = _function_id("file:///src/module.erl", "foo/-1")
    # If we reach here, no exception was raised - bug confirmed
    results.append(("negative_arity", "CONFIRMED",
        f"CONFIRMED — Negative arity not rejected. "
        f"label='foo/-1' returned {result!r} instead of raising ValueError"))
except ValueError:
    # ValueError raised as spec requires - bug NOT confirmed
    results.append(("negative_arity", "NOT CONFIRMED",
        "NOT CONFIRMED — ValueError correctly raised for negative arity"))
except Exception as e:
    results.append(("negative_arity", "ERROR",
        f"ERROR — Unexpected exception type for negative arity: {type(e).__name__}: {e}"))

# --- Bug 2: Non-string label ---
# Spec: raises ValueError when label is not a string
# Code: int.rsplit() raises AttributeError, not caught by except (ValueError, TypeError)
try:
    result = _function_id("file:///src/module.erl", 42)
    # If we reach here, no exception - unexpected
    results.append(("non_string_label", "NOT CONFIRMED",
        f"NOT CONFIRMED — Non-string label unexpectedly accepted. "
        f"label=42 returned {result!r}"))
except ValueError:
    # ValueError raised as spec requires - bug NOT confirmed
    results.append(("non_string_label", "NOT CONFIRMED",
        "NOT CONFIRMED — ValueError correctly raised for non-string label"))
except AttributeError:
    # AttributeError raised instead of ValueError - bug CONFIRMED
    results.append(("non_string_label", "CONFIRMED",
        "CONFIRMED — Non-string label raises AttributeError instead of ValueError "
        "(spec requires ValueError)"))
except Exception as e:
    results.append(("non_string_label", "ERROR",
        f"ERROR — Unexpected exception type for non-string label: {type(e).__name__}: {e}"))

# Print results
all_confirmed = all(status == "CONFIRMED" for _, status, _ in results)
for name, status, msg in results:
    print(f"[{name}] {msg}")

if all_confirmed:
    print("CONFIRMED — All bug aspects reproduced")
else:
    confirmed_count = sum(1 for _, s, _ in results if s == "CONFIRMED")
    total = len(results)
    print(f"NOT CONFIRMED — Only {confirmed_count}/{total} bug aspects reproduced")
