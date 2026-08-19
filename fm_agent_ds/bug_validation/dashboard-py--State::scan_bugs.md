# Bug Report: State::scan_bugs

**Source file:** `dashboard.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

self.bugs_confirmed, self.bugs_not_confirmed, and self.bugs_pending are updated to reflect the current state of self.bug_dir. When the directory exists, every .result.json file is classified: a file whose confirmation_status (case-insensitive) contains the substring 'confirm' without containing 'not' increments bugs_confirmed; any other file increments bugs_not_confirmed. self.bugs_pending is max(0, completed_bug_validation_stages  (bugs_confirmed + bugs_not_confirmed)). When self.bug_dir does not exist, all three counters are zero.

---

### Actual Behavior

After execution, the attributes `self.bugs_confirmed`, `self.bugs_not_confirmed`, and `self.bugs_pending` are updated according to the following rules, and no other attributes are modified. Let `E` be `self.bug_dir.exists()` before the method. If `E`, then `self.bugs_confirmed = 0`, `self.bugs_not_confirmed = 0`, and `self.bugs_pending = max(0, bv_done)` where `bv_done = sum(self.stage_counts.get('bug_validation', {}).values())` (with original value). If `E`, define:

- `F` = { p : p  self.bug_dir.glob('*.result.json') } (the set of file paths matching the pattern)
- `S` = { p  F : opening and parsing `p` as JSON succeeds without raising any exception }
- For each `p  S`, let `status(p)` = `(d.get('confirmation_status') or '').lower()` where `d` is the parsed JSON object
- `C` = { p  S : 'confirm'  status(p)  'not'  status(p) }
- `N` = `S \ C`

Then:
`self.bugs_confirmed = |C|`
`self.bugs_not_confirmed = |N|`
`bv_done` = sum of values in `self.stage_counts.get('bug_validation', {})` (as it was at method entry)
`self.bugs_pending = max(0, bv_done - |S|)`.

That is, `bugs_confirmed` counts parsed files whose lowercased confirmation status contains "confirm" but not "not"; `bugs_not_confirmed` counts the remaining parsed files (those containing "not" or neither string); `bugs_pending` is the maximum of zero and the difference between the sum of count values for the 'bug_validation' stage (or 0 if absent) and the total number of successfully parsed result files.

---

## Code Evidence

Line 4:         if not self.bug_dir.exists():
Line 5:             return

---

## Trigger Condition

When the directory does not exist, the code returns early without setting self.bugs_pending to zero. Condition A (the actual behaviour) results in self.bugs_pending being max(0, bv_done) (or retains its previous value), whereas Condition B explicitly states that all three counters must be zero.

---

## How to trigger the bug

The bug is triggered whenever `scan_bugs()` is called and `self.bug_dir` does not exist. While `bugs_confirmed` and `bugs_not_confirmed` are correctly reset to 0 at the top of the method (lines 473-474), the early return on line 476 skips the `bugs_pending` assignment on line 493. Any non-zero value of `bugs_pending` from a prior call or manual set will survive the early-exit path, violating the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `self.bug_dir` | A `Path` that does not exist on disk |
| `self.bugs_pending` (before call) | 5 (any non-zero value) |

### Expected (spec-correct) Output

`self.bugs_pending = 0`

### Actual (buggy) Output

`self.bugs_pending = 5` (unchanged)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from pathlib import Path
from dashboard import State

with tempfile.TemporaryDirectory() as tmpdir:
    state = State(tmpdir)
    state.bugs_pending = 5          # simulate a prior value
    state.scan_bugs()               # bug_dir does not exist → early return
    print(state.bugs_pending)       # 5  ← should be 0 per spec
```

---

## Probe Script

```python
import sys
import tempfile
import shutil
from pathlib import Path

# Ensure the repo root is on the module search path so "from dashboard ..." resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from dashboard import State
except Exception as e:
    print(f'ERROR: import dashboard failed — {e}')
    sys.exit(1)

tmpdir = Path(tempfile.mkdtemp())
try:
    state = State(str(tmpdir))

    # Reproduce the bug: set bugs_pending to a non-zero value, then call
    # scan_bugs() when bug_dir does not exist. The spec says all three
    # counters must become zero, but the code returns early without
    # resetting bugs_pending.
    state.bugs_pending = 5

    # Also confirm the other two ARE reset, proving only 'pending' is missed
    state.bugs_confirmed = 999
    state.bugs_not_confirmed = 999

    state.scan_bugs()

    # After scan_bugs() with a missing bug_dir, the spec requires:
    #   bugs_confirmed == 0, bugs_not_confirmed == 0, bugs_pending == 0
    expected_pending = 0
    actual_pending = state.bugs_pending

    # The bug is confirmed when actual_pending != expected_pending
    # i.e., bugs_pending was NOT reset to 0
    bug_reproduced = actual_pending != expected_pending

    if bug_reproduced:
        print(
            f'CONFIRMED — bugs_pending: {actual_pending} (should be {expected_pending}), '
            f'bugs_confirmed: {state.bugs_confirmed}, '
            f'bugs_not_confirmed: {state.bugs_not_confirmed}'
        )
    else:
        print(
            f'NOT CONFIRMED — bugs_pending matched expected: {actual_pending}, '
            f'bugs_confirmed: {state.bugs_confirmed}, '
            f'bugs_not_confirmed: {state.bugs_not_confirmed}'
        )
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — bugs_pending: 5 (should be 0), bugs_confirmed: 0, bugs_not_confirmed: 0
```
