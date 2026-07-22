# Bug Report: _phase_plan_complete

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/pipeline_setup-py/_phase_plan_complete.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns True when the file phases.json exists under work_dir, is a
    regular file, its content parses as valid JSON, and it conforms to the
    required schema (as determined by _phase_plan_schema_errors).
  - Returns False when phases.json does not exist under work_dir, is not a
    regular file, does not parse as valid JSON, or does not conform to the
    required schema.
  - The return value is idempotent for the same filesystem state: repeated
    calls with the same work_dir and same file content yield the same boolean
    result.

---

### Actual Behavior

After a call to `_phase_plan_complete(work_dir)` finishes execution, no side effects have occurred and no exceptions have been raised. The return value `r` satisfies: `r` is `True` if and only if the file obtained by `os.path.join(work_dir, "phases.json")` exists, is readable, is valid JSON, and its decoded content fully conforms to the required schema (i.e., `_phase_plan_schema_errors` returns an empty list); otherwise `r` is `False`. In formal terms: let `p = os.path.join(work_dir, "phases.json")`. Then \( \textit{result} = \mathbf{True} \leftrightarrow (\texttt{isfile}(p) \land \texttt{readable}(p) \land \textit{valid\_json}(\texttt{read}(p)) \land \textit{schema\_conforms}(\texttt{parse\_json}(\texttt{read}(p))))\), which is equivalent to \( \textit{result} = \mathbf{True} \leftrightarrow \textit{_phase_plan_schema_errors}(p) = [\,] \).

---

## Code Evidence

Line 4: return not _phase_plan_schema_errors(phases_path)

---

## Trigger Condition

The specification requires that phases.json be a regular file to return True. The code delegates entirely to _phase_plan_schema_errors, which, according to its post-condition, does not check whether the file is a regular file. If a non-regular file (e.g., a FIFO) exists, is readable, and contains valid schema-conforming JSON, _phase_plan_schema_errors returns an empty list, causing _phase_plan_complete to return True, violating the specification.

---

## How to trigger the bug

The function `_phase_plan_complete` delegates all checks to `_phase_plan_schema_errors`, which only verifies that the file is readable, contains valid JSON, and conforms to the phases schema. It does **not** check whether the file is a regular file. Therefore, if a non-regular file (such as a named pipe / FIFO) exists at `work_dir/phases.json` and contains valid schema-conforming JSON, `_phase_plan_complete` returns `True`, violating the specification which requires `False` for non-regular files.

### Inputs

| Parameter | Value |
|---|---|
| `work_dir` | A temporary directory containing a FIFO named `phases.json` |
| `phases.json` content | `{"phases": [{"modules": [{"name": "test_module", "source_files": ["test.py"]}]}]}` |

### Expected (spec-correct) Output

`False` — because `phases.json` is a FIFO (not a regular file).

### Actual (buggy) Output

`True` — because `_phase_plan_schema_errors` returns `[]` (the FIFO is readable and contains valid schema-conforming JSON), and `not []` is `True`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import json
import threading
import tempfile
import sys

sys.path.insert(0, ".")
from src import pipeline_setup

tmpdir = tempfile.mkdtemp()
fifo_path = os.path.join(tmpdir, "phases.json")
os.mkfifo(fifo_path)

valid_json = json.dumps({
    "phases": [{"modules": [{"name": "test_module", "source_files": ["test.py"]}]}]
})

def writer():
    with open(fifo_path, "w") as f:
        f.write(valid_json)

threading.Thread(target=writer, daemon=True).start()

result = pipeline_setup._phase_plan_complete(tmpdir)
print(result)  # actual (buggy) output: True
# expected (correct) output: False

os.unlink(fifo_path)
os.rmdir(tmpdir)
```

---

## Probe Script

```python
import sys
import os
import json
import threading
import tempfile

# Add repo root to sys.path so that `from src import pipeline_setup` works
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src import pipeline_setup
except ImportError as e:
    print(f"ERROR: Cannot import src.pipeline_setup: {e}")
    sys.exit(1)

try:
    # Create a fresh temporary directory for the probe workspace
    tmpdir = tempfile.mkdtemp()
    fifo_path = os.path.join(tmpdir, "phases.json")

    # Create a named pipe (FIFO) — this is NOT a regular file
    os.mkfifo(fifo_path)

    # Valid JSON content that conforms to the phases.json schema
    valid_json = json.dumps({
        "phases": [
            {
                "modules": [
                    {
                        "name": "test_module",
                        "source_files": ["test.py"]
                    }
                ]
            }
        ]
    })

    # Thread synchronisation event for ordered teardown
    writer_done = threading.Event()

    def writer():
        """Write valid schema-conforming JSON into the FIFO."""
        try:
            with open(fifo_path, "w") as f:
                f.write(valid_json)
        except Exception:
            pass
        finally:
            writer_done.set()

    wt = threading.Thread(target=writer, daemon=True)
    wt.start()

    # Call the function under test.
    # _phase_plan_complete opens the FIFO for reading, which unblocks
    # the writer's open-for-write, data flows, and both sides close.
    actual = pipeline_setup._phase_plan_complete(tmpdir)

    # Wait for the writer to finish before cleanup
    writer_done.wait(timeout=10)
    wt.join(timeout=1)

    # Cleanup the FIFO and temporary directory
    try:
        os.unlink(fifo_path)
    except OSError:
        pass
    try:
        os.rmdir(tmpdir)
    except OSError:
        pass

    # The specification says: return False when phases.json is NOT a regular file.
    # A FIFO is NOT a regular file, so the expected (spec-correct) value is False.
    expected = False

    if actual != expected:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: True | expected: False
```
