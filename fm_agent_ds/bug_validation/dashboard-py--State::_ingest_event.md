# Bug Report: State::_ingest_event

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/dashboard.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

The specification requires verification counters to be incremented only when purpose is 'check_post_implies_spec', but these branches increment self.verification_mismatch and self.verification_error unconditionally, so a non-verification llm_call event with status 'mismatch' or 'error' incorrectly increments the respective counter.

---

### Actual Behavior

After the normal execution of `_ingest_event` (no unhandled exceptions), the following holds for the object `self`.

Let `pre` denote the object state immediately before the call, `post` the state immediately after. Let `stage = ev.get("stage", "?")`, `status = ev.get("status", "?")`, `et = ev.get("type")`. Let `start = _parse_iso(ev.get("start_time"))` and `end = _parse_iso(ev.get("end_time"))`.

1. First/Last time updates:
   - `post.first_event_time = start` if `start is not None` and (`pre.first_event_time is None` or `start < pre.first_event_time`), else `pre.first_event_time`.
   - `post.last_event_time = end` if `end is not None` and (`pre.last_event_time is None` or `end > pre.last_event_time`), else `pre.last_event_time`.

2. Stage counter:
   - `post.stage_counts[stage][status] = pre.stage_counts[stage][status] + 1`.

3. Conditional on event type:

   (A) If `et == "llm_call"`:
        Let `md = ev.get("metadata", {})`, `model = md.get("model")`.
        a. `post.model_seen = model` if `model` is truthy and `not pre.model_seen` is truthy, else `pre.model_seen`.
        b. Token cost processing... (token totals and cost updated from usage metadata)
        c. Verification counters:
           - If `status == "success"` AND `md.get("purpose") == "check_post_implies_spec"`: `verification_success += 1`.
           - Elif `status == "mismatch"`: `verification_mismatch += 1` (unconditional — no purpose check).
           - Elif `status == "error"`: `verification_error += 1` (unconditional — no purpose check).

---

## Code Evidence

```python
# Line 298-303 of dashboard.py
            if status == "success" and md.get("purpose") == "check_post_implies_spec":
                self.verification_success += 1
            elif status == "mismatch":
                self.verification_mismatch += 1
            elif status == "error":
                self.verification_error += 1
```

The `success` branch (line 298) correctly checks that `md.get("purpose") == "check_post_implies_spec"` before incrementing. However, the `mismatch` (line 300-301) and `error` (line 302-303) branches lack this guard, incrementing their respective counters unconditionally for ANY llm_call event with the given status, regardless of purpose.

---

## Trigger Condition

A non-verification llm_call event with status 'mismatch' or 'error' incorrectly increments the respective counter.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|---|---|
| `ev["type"]` | `"llm_call"` |
| `ev["status"]` | `"mismatch"` |
| `ev["metadata"]["purpose"]` | `"some_other_purpose"` (not `"check_post_implies_spec"`) |

### Expected (spec-correct) Output

`self.verification_mismatch` unchanged (0) — purpose is not `check_post_implies_spec`.

### Actual (buggy) Output

`self.verification_mismatch` incremented to 1 — the branch does not check purpose.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from dashboard import State
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    state = State(tmpdir)
    print("Before: verification_mismatch =", state.verification_mismatch)
    state._ingest_event({
        "type": "llm_call",
        "status": "mismatch",
        "stage": "verification",
        "metadata": {"purpose": "some_other_purpose"},
    })
    print("After:  verification_mismatch =", state.verification_mismatch)
    # actual (buggy) output: After: verification_mismatch = 1
    # expected (correct) output: After: verification_mismatch = 0
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — verification_mismatch: 0 -> 1 (incorrectly incremented for non-verification event) | verification_error: 0 -> 1 (incorrectly incremented for non-verification event)
```
