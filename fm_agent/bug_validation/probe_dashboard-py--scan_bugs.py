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
