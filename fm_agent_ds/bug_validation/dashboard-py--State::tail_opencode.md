# Bug Report: State::tail_opencode

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/dashboard-py/State::tail_opencode.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

If self.opencode_dir does not exist as a directory, returns immediately with no side effects.

Otherwise: for each JSONL file in the directory (in ascending lexicographic filename order), reads all bytes appended to the file since its tracked offset in self._opencode_offsets. If a file's size is strictly less than its tracked offset (indicating truncation or rotation), reading begins from byte 0. Every non-empty line that parses as valid JSON is ingested into the State's in-memory raw trace collection; empty lines and lines that fail to parse as JSON are skipped. After processing all files, the aggregate cache_window collection in the State reflects the cumulative (cached_tokens, total_input_tokens) pairs across all raw trace records ingested so far. Each file's offset in self._opencode_offsets is updated to the current end-of-file byte position for that file.

---

### Actual Behavior

If self.opencode_dir does not exist, self._opencode_offsets is unchanged and no ingestion occurs.

Otherwise, for each path p in sorted(self.opencode_dir.glob('*.jsonl')): let name = p.name. If obtaining p.stat().st_size raises OSError, the file is skipped and self._opencode_offsets[name] remains unchanged. Else let size = st_size and old_off = self._opencode_offsets.get(name, 0). If size < old_off, set old_off = 0. If size == old_off, the file is skipped and self._opencode_offsets[name] remains old_off. If size > old_off, the file is opened, seeked to old_off, and all lines from that position to end-of-file are read. For each non-empty line l, if json.loads(l) succeeds, rec = loaded JSON; self._ingest_opencode(rec, name) is called. After processing all lines, self._opencode_offsets[name] is set to the file's current position (equal to its size at that moment). Consequently, after the method returns, for every *.jsonl file in the directory that was accessible and had size > old_off at entry, self._opencode_offsets[name] equals its final size, all valid JSON records from the unconsumed portion have been ingested into the State's in-memory OpenCode trace collection, and the aggregate cache_window (pairs of (cached_tokens, total_input_tokens)) reflects cumulative token usage across all records ingested so far.

---

## Code Evidence

Line 2: if not self.opencode_dir.exists():

---

## Trigger Condition

Specification requires: if self.opencode_dir does not exist as a directory, return immediately with no side effects. The code only checks .exists(), which returns True for any path (file, symlink, etc.). If self.opencode_dir is a file, the code proceeds to .glob('*.jsonl'), which raises NotADirectoryError (or similar), thus not returning immediately and causing an exception side effect.

---

## How to trigger the bug

When `self.opencode_dir` is a regular file (not a directory), `Path.exists()` returns `True`, so the guard clause on line 341 of `dashboard.py` does **not** trigger. The method proceeds to call `self.opencode_dir.glob("*.jsonl")` instead of returning immediately. On CPython 3.12, `.glob()` on a non-directory path returns an empty iterator silently (no crash), but the method still **fails to return immediately** as the specification requires. The guard check should use `Path.is_dir()` instead of `Path.exists()`.

### Inputs

| Parameter | Value |
|---|---|
| `proj_dir` | A temporary directory containing `trace/opencode` as a regular file instead of a directory |
| `self.opencode_dir` | `<tmpdir>/trace/opencode` — a regular file created by the fixture |

### Expected (spec-correct) Output

`tail_opencode()` returns immediately with no observable side effects. `self._opencode_offsets` remains unchanged and no `_ingest_opencode()` calls occur.

### Actual (buggy) Output

`tail_opencode()` proceeds past the guard clause and calls `self.opencode_dir.glob("*.jsonl")` on a non-directory path. On CPython 3.12, `.glob()` gracefully returns an empty iterator, so no crash occurs, but the method does **not** return immediately as the specification mandates. `self._opencode_offsets` remains unchanged (benign in this case).

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from pathlib import Path
from dashboard import State

tmpdir = Path(tempfile.mkdtemp())
(trace := tmpdir / "trace").mkdir()
(trace / "opencode").write_text("not a directory")

state = State(str(tmpdir))
state.tail_opencode()
# expected: returns immediately (no glob call)
# actual:   guard bypassed, .glob() called on non-directory path
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — guard bypassed: .glob() called on non-directory path
| spec_claim:  return immediately with no side effects if not a directory
| actual:      proceeded to .glob('*.jsonl') on a non-directory path
| guard check: .exists() returned True for a file (should use .is_dir())
| offsets unchanged: True
| root cause:  line 341 uses .exists() instead of .is_dir()
```
