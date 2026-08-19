"""Probe for bug src--languages--rust-py--batch_extract.

Spec claim: the Rust batch_extract backend must return None when the
codegraph index is unavailable (never an empty dict), so callers can record
the language as having an unavailable backend and apply the regex fallback.

Trigger: call the rust language handler's batch_extract (exposed through the
public registry facade src.languages.registry) on a project directory that
has no .codegraph/codegraph.db index. Buggy code returns {} instead of None.

FM-Agent self-validation guard: this probe only exercises the smallest unit
(the registry's rust batch_extract handler) with a fresh temporary fixture
directory; it does not start any FM-Agent workflow.
"""

import os
import sys
import tempfile

# Ensure the repo root is importable regardless of the launch directory.
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

fixture = None
try:
    from src.languages.registry import REGISTRY

    # Fresh temporary project directory owned by the probe; no files are
    # written anywhere in the active repository.
    fixture = tempfile.mkdtemp(prefix="fm_probe_rust_py_")

    # Sanity-check the trigger precondition: no codegraph index at the
    # fixture dir nor at its immediate parent (the two locations
    # CodeGraphExtractor.from_proj_dir checks).
    for candidate in (fixture, os.path.dirname(os.path.abspath(fixture))):
        index = os.path.join(candidate, ".codegraph", "codegraph.db")
        if os.path.exists(index):
            print(f"ERROR: unexpected codegraph index at {index}")
            sys.exit(1)

    rust_handler = REGISTRY["rust"]
    actual = rust_handler.batch_extract(fixture)
    expected = None  # spec: backend unavailable -> None, never {}
    passed = actual != expected  # True -> bug reproduced
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)
finally:
    if fixture and os.path.isdir(fixture):
        try:
            os.rmdir(fixture)  # fixture is an empty temp dir
        except OSError:
            pass

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
