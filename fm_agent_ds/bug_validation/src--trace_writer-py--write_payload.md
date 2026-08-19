# Bug Report: write_payload

**Source file:** `src/trace_writer.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

The entire content is stored in a file within the trace payload subdirectory of trace_dir. The filename consists of event_id and name joined by a single underscore character. The write is atomic: any observer of the filesystem sees either the file absent (or in its prior state) or the file containing the complete new content; no intermediate or partial content is ever visible. Returns the relative path from the parent directory of trace_dir to the stored file, expressed with the platform's native path separator.

---

### Actual Behavior

On normal completion: The file at the path formed by os.path.join(payload_dir, f"{event_id}_{name}") exists and contains exactly the data from `content` (UTF-8 encoded if `binary` is False; raw bytes if `binary` is True). The temporary file at the path with ".tmp" suffix no longer exists. The return value is the relative path from the parent directory of `trace_dir` to that file, computed by os.path.relpath. If any exception occurs before os.replace completes successfully, the function does not return normally: the target file (if it previously existed) remains unchanged, and the temporary file may exist with partial or full content, but no guarantee is made about its state.

---

## Code Evidence

Line 27: path = os.path.join(payload_dir, f"{event_id}_{name}")
Line 28: tmp_path = path + ".tmp"

---

## Trigger Condition

If event_id or name contains path separators (e.g., name='../../hacked'), the constructed path escapes the payload subdirectory (e.g., /tmp/trace/.trace/hacked). The specification requires the file to be stored within the trace payload subdirectory, but the code does not enforce this, allowing writes to arbitrary locations.

---

## How to trigger the bug

The bug is triggered when `event_id` or `name` contains path separators (`/`) that, after being joined into the filename `f"{event_id}_{name}"`, produce standalone `..` components. These cause the resolved path to escape the `payloads/` subdirectory. For example, `event_id = "../../"` produces the path component `..` followed by another `..`, which traverses above `payload_dir` and `trace_dir` into the parent directory.

### Inputs

| Parameter | Value |
|-----------|-------|
| trace_dir | `<tmpdir>/.trace` |
| event_id | `../../` |
| name | `escaped_file` |
| content | `malicious content` |

### Expected (spec-correct) Output

A relative path pointing to a file within `<tmpdir>/.trace/payloads/`. The spec requires "stored in a file within the trace payload subdirectory."

### Actual (buggy) Output

The file is written at `<tmpdir>/_escaped_file` (outside the `payloads/` subdirectory, two levels above it at `<tmpdir>/`). The relative path returned points to a location outside `payloads/`.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
from src.trace_writer import write_payload

with tempfile.TemporaryDirectory() as tmpdir:
    trace_dir = os.path.join(tmpdir, ".trace")
    
    # event_id with path traversal escapes payload_dir
    rel = write_payload(trace_dir, event_id="../../", name="escaped_file", content="malicious")
    
    written = os.path.join(os.path.dirname(trace_dir), rel)
    payload_dir = os.path.join(trace_dir, "payloads")
    escaped = not os.path.realpath(written).startswith(os.path.realpath(payload_dir))
    print(f"Escaped payload dir: {escaped}")
    print(f"Written to: {written}")
# actual (buggy) output: written outside trace_dir/payloads/
# expected (correct) output: written inside trace_dir/payloads/
```

---

## Probe Script

```python
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.trace_writer import write_payload


def probe():
    with tempfile.TemporaryDirectory(prefix="bug_probe-") as tmpdir:
        trace_dir = os.path.join(tmpdir, ".trace")
        payload_dir = os.path.join(trace_dir, "payloads")

        # Use event_id with path traversal characters so that
        # f"{event_id}_{name}" produces standalone ".." components
        # e.g., "{../../}_{hacked}" → "../../_hacked" escapes payload_dir
        event_id = "../../"
        name = "escaped_file"

        try:
            rel_path = write_payload(
                trace_dir=trace_dir,
                event_id=event_id,
                name=name,
                content="malicious content",
            )
        except Exception as e:
            print(f"ERROR: {e}")
            return False

        # Resolve the written file to an absolute path
        written_path = os.path.normpath(os.path.join(os.path.dirname(trace_dir), rel_path))
        payload_dir_real = os.path.realpath(payload_dir)
        written_path_real = os.path.realpath(written_path)

        # Check: is the written file inside the payloads directory?
        inside = written_path_real.startswith(payload_dir_real + os.sep)

        return not inside


if __name__ == "__main__":
    import sys as _sys

    # The package is at the repo root, sys.path already adjusted above
    try:
        bug_reproduced = probe()
        if bug_reproduced:
            print("CONFIRMED — path traversal: file escaped the payload subdirectory")
        else:
            print("NOT CONFIRMED — file remained inside the payload subdirectory")
    except Exception as exc:
        print(f"ERROR: {exc}")
        _sys.exit(1)
```

### Probe Output

```
CONFIRMED — path traversal: file escaped the payload subdirectory
```
