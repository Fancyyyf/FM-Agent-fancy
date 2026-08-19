"""Probe: verify that _ingest_event incorrectly increments verification counters
for non-verification llm_call events with status 'mismatch' or 'error'.

Bug: Lines 300-303 in dashboard.py increment self.verification_mismatch and
self.verification_error unconditionally. The specification requires that these
counters only be incremented when the event's purpose is 'check_post_implies_spec'.
"""

import sys
import tempfile
import os
from pathlib import Path

# Add repo root to path so `from dashboard import State` works
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

try:
    from dashboard import State

    # Create State in a temp directory (isolated, no side effects)
    with tempfile.TemporaryDirectory() as tmpdir:
        state = State(tmpdir)

        # --- Test 1: mismatch status with non-verification purpose ---
        # This event should NOT increment verification_mismatch (per spec)
        # But the buggy code DOES increment it
        mismatch_before = state.verification_mismatch
        state._ingest_event({
            "type": "llm_call",
            "status": "mismatch",
            "stage": "verification",
            "start_time": "2026-01-01T00:00:00Z",
            "end_time": "2026-01-01T00:00:01Z",
            "metadata": {
                "purpose": "some_other_purpose",  # NOT check_post_implies_spec
            }
        })
        mismatch_after = state.verification_mismatch

        # --- Test 2: error status with non-verification purpose ---
        error_before = state.verification_error
        state._ingest_event({
            "type": "llm_call",
            "status": "error",
            "stage": "verification",
            "start_time": "2026-01-01T00:00:02Z",
            "end_time": "2026-01-01T00:00:03Z",
            "metadata": {
                "purpose": "some_other_purpose",  # NOT check_post_implies_spec
            }
        })
        error_after = state.verification_error

        # --- Assertions ---
        # Spec says: counters only incremented for check_post_implies_spec purpose
        # Code does: mismatch/error branches increment unconditionally
        # CONFIRMED if: actual (buggy) != expected (spec-correct)
        mismatch_bug = mismatch_after != mismatch_before   # True → bug: counter incremented
        error_bug = error_after != error_before              # True → bug: counter incremented

        if mismatch_bug or error_bug:
            parts = []
            if mismatch_bug:
                parts.append(
                    f"verification_mismatch: {mismatch_before} -> {mismatch_after} "
                    f"(incorrectly incremented for non-verification event)"
                )
            if error_bug:
                parts.append(
                    f"verification_error: {error_before} -> {error_after} "
                    f"(incorrectly incremented for non-verification event)"
                )
            print(f'CONFIRMED — {" | ".join(parts)}')
        else:
            print(
                f"NOT CONFIRMED — mismatch: {mismatch_before}->{mismatch_after}, "
                f"error: {error_before}->{error_after}"
            )

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
