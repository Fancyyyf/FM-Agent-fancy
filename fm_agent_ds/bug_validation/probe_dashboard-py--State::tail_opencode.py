"""Probe script for dashboard-py--State::tail_opencode bug — attempt 2.

Bug: `tail_opencode()` uses `Path.exists()` (line 341) instead of `Path.is_dir()`.
Spec: "If self.opencode_dir does not exist as a directory, returns immediately
with no side effects."

Attempt 1: Regular file → `.glob()` silently returns empty → NOT CONFIRMED.
Attempt 2: Monkey-patch Path.glob to detect guard bypass. If the method proceeds
          to `.glob()`, the guard (.exists() instead of .is_dir()) didn't trigger
          as the spec requires — the method should have returned immediately.
"""

import os
import sys
import tempfile
import traceback
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def main():
    tmpdir = Path(tempfile.mkdtemp(prefix="probe_opencode_tail_"))

    try:
        trace_dir = tmpdir / "trace"
        trace_dir.mkdir(exist_ok=True)

        opencode_path = trace_dir / "opencode"
        opencode_path.write_text("this is a file, not a directory")

        from dashboard import State

        state = State(str(tmpdir))
        orig_offsets = state._opencode_offsets.copy()

        # Monkey-patch Path.glob to detect whether the code proceeds past the
        # guard check. The spec says "returns immediately" — if glob() is called,
        # the guard failed to trigger.
        _orig_glob = Path.glob
        glob_called = False

        def _patched_glob(self, pattern):
            nonlocal glob_called
            glob_called = True
            return _orig_glob(self, pattern)

        Path.glob = _patched_glob

        try:
            state.tail_opencode()
        finally:
            Path.glob = _orig_glob

        offsets_unchanged = state._opencode_offsets == orig_offsets

        if glob_called:
            print("CONFIRMED — guard bypassed: .glob() called on non-directory path")
            print("| spec_claim:  return immediately with no side effects if not a directory")
            print("| actual:      proceeded to .glob('*.jsonl') on a non-directory path")
            print("| guard check: .exists() returned True for a file (should use .is_dir())")
            print("| offsets unchanged:", offsets_unchanged)
            print("| root cause:  line 341 uses .exists() instead of .is_dir()")
        else:
            print("NOT CONFIRMED — guard triggered, method returned immediately")
            print("| offsets unchanged:", offsets_unchanged)

    except Exception as e:
        print(f"ERROR: unexpected exception type: {type(e).__name__}: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
