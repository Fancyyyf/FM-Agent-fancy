# Bug Report: _setup_outputs_complete

**Source file:** `src/pipeline_setup.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns True when phases.json, engine_overview.txt, and at least one file whose name matches the pattern phase_NN_types.txt (where NN is one or more digits) all exist as regular files under work_dir.
  - Returns False when any one of the three required output categories is absent from work_dir.

---

### Actual Behavior

After the function returns, the boolean result R satisfies: R = True if and only if (a) a regular file "phases.json" exists under "work_dir", its content parses as valid JSON and conforms to the required schema, and (b) both "engine_overview.txt" and at least one regular file matching the pattern "phase_NN_types.txt" (with NN one or more digits) exist under "work_dir". Otherwise R = False. The "work_dir" path is unchanged.

---

## Code Evidence

Line 3

---

## Trigger Condition

The code returns False if phases.json is not valid JSON/schema-conformant, but the specification only requires the file's existence. Hence, for an input where phases.json exists but is invalid JSON, the code returns False while the specification mandates True.

---

## How to trigger the bug

`_setup_outputs_complete` delegates to `_phase_plan_complete`, which calls `_phase_plan_schema_errors` that validates both JSON parseability and schema conformance of `phases.json`. The specification only requires that `phases.json` exists as a regular file — it says nothing about valid JSON or schema conformance. Therefore, when `phases.json` exists on disk but contains invalid JSON (e.g., the text `"this is not valid json {{{"`), the code returns `False`, while the specification mandates `True` (since all three output categories exist).

### Inputs

| Parameter | Value |
|-----------|-------|
| `work_dir` | A temporary directory containing: `phases.json` (exists, invalid JSON content `"this is not valid json {{{"`), `spec_prompts/domain_context/engine_overview.txt` (exists), `spec_prompts/domain_context/phase_01_types.txt` (exists) |

### Expected (spec-correct) Output

`True` — all three required output categories (phases.json, engine_overview.txt, phase_NN_types.txt) exist as regular files under work_dir.

### Actual (buggy) Output

`False` — `_phase_plan_complete` returns `False` because `phases.json` is not valid JSON, causing `_setup_outputs_complete` to return `False`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
import sys
sys.path.insert(0, ".")

from src.pipeline_setup import _setup_outputs_complete

with tempfile.TemporaryDirectory() as tmpdir:
    domain_dir = os.path.join(tmpdir, "spec_prompts", "domain_context")
    os.makedirs(domain_dir, exist_ok=True)
    with open(os.path.join(domain_dir, "engine_overview.txt"), "w") as f:
        f.write("dummy overview")
    with open(os.path.join(domain_dir, "phase_01_types.txt"), "w") as f:
        f.write("dummy types")
    with open(os.path.join(tmpdir, "phases.json"), "w") as f:
        f.write("this is not valid json {{{")

    result = _setup_outputs_complete(tmpdir)
    print(result)  # actual (buggy) output: False
    # expected (correct) output: True
```

---

## Probe Script

```python
"""Probe script for bug: _setup_outputs_complete validates JSON schema instead of
only checking file existence.

Spec claim: Returns True when phases.json, engine_overview.txt, and at least one
phase_NN_types.txt all exist as regular files under work_dir.

Actual behavior: Returns False when phases.json is not valid JSON/schema-conformant,
even though all three required output categories exist on disk.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.pipeline_setup import _setup_outputs_complete

with tempfile.TemporaryDirectory() as tmpdir:
    # Create engine_overview.txt (exists)
    with open(os.path.join(tmpdir, "engine_overview.txt"), "w") as f:
        f.write("dummy overview")

    # Create phase_01_types.txt (exists)
    with open(os.path.join(tmpdir, "phase_01_types.txt"), "w") as f:
        f.write("dummy types")

    # Create spec_prompts/domain_context/ subdirectory structure for
    # _domain_context_complete to find the files
    domain_dir = os.path.join(tmpdir, "spec_prompts", "domain_context")
    os.makedirs(domain_dir, exist_ok=True)
    with open(os.path.join(domain_dir, "engine_overview.txt"), "w") as f:
        f.write("dummy overview")
    with open(os.path.join(domain_dir, "phase_01_types.txt"), "w") as f:
        f.write("dummy types")

    # Create phases.json that EXISTS but is INVALID JSON
    # This satisfies the spec's existence requirement, but _phase_plan_complete
    # will return False because it checks JSON validity + schema.
    with open(os.path.join(tmpdir, "phases.json"), "w") as f:
        f.write("this is not valid json {{{")

    try:
        actual = _setup_outputs_complete(tmpdir)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Spec says: "Returns True when phases.json, engine_overview.txt, and at least
    # one file matching phase_NN_types.txt all exist as regular files under work_dir."
    # All three exist, so expected = True.
    expected = True

    # The bug is that the code returns False when phases.json is invalid JSON,
    # even though all files exist. So the bug is confirmed if actual != expected.
    passed = actual != expected

    if passed:
        print(f"CONFIRMED -- actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED -- actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED -- actual: False | expected: True
```
