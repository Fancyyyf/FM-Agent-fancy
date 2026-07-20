# Bug Report: scan_bugs

**Source file:** `dashboard.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- self.bugs_confirmed equals the number of *.result.json files in
    self.bug_dir whose parsed "confirmation_status" field, after
    lowercasing, contains the substring "confirm".
  - self.bugs_not_confirmed equals the number of remaining *.result.json
    files in self.bug_dir  those whose parsed "confirmation_status"
    field, after lowercasing, does NOT contain "confirm", including files
    where the field is absent, the file cannot be read, or the content is
    not valid JSON.
  - self.bugs_pending equals max(0, C - (self.bugs_confirmed +
    self.bugs_not_confirmed)), where C is the sum of all integer values
    under self.stage_counts["bug_validation"], or 0 if the key
    "bug_validation" is absent from self.stage_counts.
  - If self.bug_dir does not exist, self.bugs_confirmed,
    self.bugs_not_confirmed, and self.bugs_pending are all set to 0 and
    no directory scanning occurs.

---

### Actual Behavior

If self.bug_dir does not exist at the start of the method, then self.bugs_confirmed = 0, self.bugs_not_confirmed = 0, and self.bugs_pending remains unchanged. Otherwise, let F be the set of paths in self.bug_dir.glob('*.result.json') for which open and json.load succeed without raising an Exception. For each f in F, let S(f) = (json.load(f).get('confirmation_status') or '').lower(). Define C = { f in F | 'confirm' in S(f) and 'not' not in S(f) }. Then self.bugs_confirmed = |C|, self.bugs_not_confirmed = |F \ C|, and self.bugs_pending = max(0, sum(self.stage_counts.get('bug_validation', {}).values()) - (self.bugs_confirmed + self.bugs_not_confirmed)). No other attributes are modified.

---

## Code Evidence

Line 4-5: return early without resetting bugs_pending; Line 10-11: silently skip unreadable/invalid JSON files instead of counting them as bugs_not_confirmed.

---

## Trigger Condition

Specification requires bugs_pending set to 0 when directory missing; code leaves it unchanged. Specification requires unreadable/invalid JSON files be counted as bugs_not_confirmed; code skips them entirely.

---

## How to trigger the bug

The `scan_bugs` method has two spec violations:

### Bug 1 — bugs_pending not reset when bug_dir missing

When `self.bug_dir` does not exist, the method sets `bugs_confirmed` and `bugs_not_confirmed` to 0 but returns early without resetting `bugs_pending`. If `bugs_pending` was previously set to a non-zero value (e.g., from a prior call where `bug_dir` existed), it retains the stale value instead of being reset to 0.

### Bug 2 — Invalid JSON files silently skipped

When a `*.result.json` file contains invalid JSON (or cannot be read), the `except Exception: continue` on line 481-482 silently skips it. According to the specification, these files must be counted as `bugs_not_confirmed`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `state.bugs_pending` (pre-set) | `42` |
| `state.bug_dir` | A non-existent path (for Bug 1) / A temp dir with mixed valid/invalid JSON files (for Bug 2) |
| Temp dir contents | `valid_confirmed.result.json` (valid JSON, status "confirmed"), `invalid_json.result.json` (invalid JSON), `missing_status.result.json` (valid JSON, no `confirmation_status` field) |

### Expected (spec-correct) Output

Bug 1: `bugs_pending` = `0` (reset when `bug_dir` missing)
Bug 2: `bugs_confirmed` = `1`, `bugs_not_confirmed` = `2` (invalid JSON counted as not_confirmed)

### Actual (buggy) Output

Bug 1: `bugs_pending` = `42` (unchanged from prior value)
Bug 2: `bugs_confirmed` = `1`, `bugs_not_confirmed` = `1` (invalid JSON silently skipped)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from dashboard import State

# Bug 1: bugs_pending not reset
state = State("/path/to/project")
state.bugs_pending = 42
state.bug_dir = state.workdir / "nonexistent_dir"
state.scan_bugs()
assert state.bugs_pending == 0  # spec says 0
# actual (buggy) output: 42
# expected (correct) output: 0

# Bug 2: invalid JSON not counted
# Create a temp dir with {not valid json}.result.json
# state.bug_dir = temp_path
# state.scan_bugs()
# expected bugs_not_confirmed includes the invalid file; actual does not
```

---

## Probe Script

```python
"""Probe script for dashboard-py--scan_bugs: test two spec violations.

Bug 1: bugs_pending not reset to 0 when bug_dir missing.
Bug 2: Invalid/unreadable JSON files silently skipped instead of counted as bugs_not_confirmed.
"""
import sys
import tempfile
import json as json_mod
from pathlib import Path

from dashboard import State

bugs_found = 0

# ── Bug 1: bugs_pending not reset when bug_dir missing ──
state = State("/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot")
state.bugs_pending = 42  # simulate a prior scan_bugs run that set this
state.bug_dir = state.workdir / "nonexistent_dir_for_probe"
state.scan_bugs()

expected_pending = 0
actual_pending = state.bugs_pending
if actual_pending != expected_pending:
    bugs_found += 1
    print(f'BUG1 CONFIRMED (bugs_pending): actual={actual_pending!r}, expected={expected_pending!r}')
else:
    print(f'BUG1 NOT CONFIRMED (bugs_pending): actual={actual_pending!r}')

# ── Bug 2: Invalid JSON files not counted as bugs_not_confirmed ──
with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)
    # Valid: confirmed status
    (tmp / "valid_confirmed.result.json").write_text(
        json_mod.dumps({"confirmation_status": "confirmed"})
    )
    # Invalid: not valid JSON — spec says this must be counted as bugs_not_confirmed
    (tmp / "invalid_json.result.json").write_text("{not valid json")
    # Valid: missing confirmation_status — falls into else branch, counted as not_confirmed
    (tmp / "missing_status.result.json").write_text(json_mod.dumps({}))

    state2 = State("/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot")
    state2.bug_dir = tmp
    state2.scan_bugs()

    # Expected per spec:
    #   bugs_confirmed = 1  (valid_confirmed)
    #   bugs_not_confirmed = 2 (invalid_json + missing_status)
    # Actual (buggy):
    #   bugs_confirmed = 1  (valid_confirmed)
    #   bugs_not_confirmed = 1 (missing_status only; invalid_json silently skipped via 'except: continue')

    expected_confirmed = 1
    expected_not_confirmed = 2
    actual_confirmed = state2.bugs_confirmed
    actual_not_confirmed = state2.bugs_not_confirmed

    issues = []
    if actual_not_confirmed != expected_not_confirmed:
        issues.append(
            f'bugs_not_confirmed: actual={actual_not_confirmed!r}, expected={expected_not_confirmed!r}'
        )
    if actual_confirmed != expected_confirmed:
        issues.append(
            f'bugs_confirmed: actual={actual_confirmed!r}, expected={expected_confirmed!r}'
        )

    if issues:
        bugs_found += 1
        print(f'BUG2 CONFIRMED (invalid json): {"; ".join(issues)}')
    else:
        print(f'BUG2 NOT CONFIRMED: all counts matched expected')

# ── Final verdict ──
if bugs_found > 0:
    print(f'CONFIRMED — {bugs_found} bug(s) reproduced')
else:
    print('NOT CONFIRMED')
```

### Probe Output

```
BUG1 CONFIRMED (bugs_pending): actual=42, expected=0
BUG2 CONFIRMED (invalid json): bugs_not_confirmed: actual=1, expected=2
CONFIRMED — 2 bug(s) reproduced
```
