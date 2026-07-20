# Bug Report: write_payload

**Source file:** `src/trace_writer.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- The content is atomically written to a file named "{event_id}_{name}"
    under the payloads subdirectory of trace_dir. The write is atomic: the
    file either appears at the final path in its entirety or not at all;
    no partial content is visible at that path.
  - When binary is falsy, content is written as UTF-8-encoded text.
  - When binary is truthy, content is written as raw bytes.
  - Returns a relative path string that identifies the written file for
    later retrieval. The path is relative to the directory one level above
    trace_dir and uses the operating-system path separator.
  - The necessary parent directories for the file are created under
    trace_dir as a side effect.

---

### Actual Behavior

If the function raises an exception (e.g., OSError, IOError), no guarantees are made about the existence or content of the target file. If the function returns normally, the returned value `r` satisfies: `r = os.path.relpath(p, os.path.dirname(trace_dir))` where `p = os.path.join(payload_dir, event_id + '_' + name)` and `payload_dir = _ensure_trace_dirs(trace_dir)`. The file at `p` exists, is a regular file, and its content exactly matches the input `content`. If `binary` is truthy, the file contains the raw bytes of `content`; otherwise, the file contains the string `content` encoded in UTF-8. The write is atomic: the file at `p` is either the newly written content or its prior content (if any) remains unmodified. The temporary file used during the write does not persist. The directory `payload_dir` exists and is a subdirectory of `trace_dir`.

---

## Code Evidence

Line 10: return os.path.relpath(path, os.path.dirname(trace_dir))

---

## Trigger Condition

When trace_dir is '.', os.path.dirname(trace_dir) returns '.' instead of the parent directory '..'. The specification requires the returned path to be relative to the directory one level above trace_dir. Hence, the code produces a path relative to the trace_dir itself, not its parent, violating the specification.

---

## How to trigger the bug

When `write_payload` is called with `trace_dir="."`, `os.path.dirname(".")` returns `""` (empty string), which is semantically equivalent to the current directory — the same as `trace_dir` itself. The specification requires the returned path to be relative to the directory **one level above** `trace_dir` (i.e., `".."`). The actual implementation therefore returns a path relative to the wrong base directory.

### Inputs

| Parameter | Value |
|-----------|-------|
| trace_dir | `"."` |
| event_id  | `"evt1"` |
| name      | `"test"` |
| content   | `"hello"` |
| binary    | `False` (default) |

### Expected (spec-correct) Output

`"<tmpdir_name>/payloads/evt1_test"` — a path relative to the directory one level above `trace_dir` (i.e., `..`).

### Actual (buggy) Output

`"payloads/evt1_test"` — a path relative to `trace_dir` itself (i.e., `.`), because `os.path.dirname(".")` returns `""`.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
from src.trace_writer import write_payload

result = write_payload(".", "evt1", "test", "hello")
# actual (buggy) output: "payloads/evt1_test"
# expected (correct) output: "<parent_dir_name>/payloads/evt1_test"
```

---

## Probe Script

```python
import sys, os, tempfile, shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.trace_writer import write_payload

    tmpdir = tempfile.mkdtemp()
    orig_cwd = os.getcwd()

    try:
        os.chdir(tmpdir)

        # Call write_payload with trace_dir=".", the trigger condition
        result = write_payload(".", "evt1", "test", "hello")

        # The spec says the returned path must be relative to
        # "the directory one level above trace_dir".
        # For trace_dir=".", one level above is "..", whose absolute path
        # is os.path.dirname(tmpdir).
        #
        # Expected: relpath from parent-of-trace_dir to the written file
        expected = os.path.relpath(
            os.path.join(tmpdir, "payloads", "evt1_test"),
            os.path.dirname(tmpdir),
        )

        # Bug check: the actual result is relative to os.path.dirname(".")
        # which is "" (effectively "." / same as trace_dir), NOT "..".
        passed = result != expected

        if passed:
            print(f"CONFIRMED — actual: {result!r} | expected: {expected!r}")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {result!r}")
    finally:
        os.chdir(orig_cwd)
        shutil.rmtree(tmpdir, ignore_errors=True)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: 'payloads/evt1_test' | expected: 'tmpjkfzjss_/payloads/evt1_test'
```
