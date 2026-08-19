# Bug Report: load_staged_domain_knowledge_text

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/domain_knowledge-py/load_staged_domain_knowledge_text.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a string containing the concatenated full text of all staged domain knowledge files, formatted for injection into an LLM prompt. If no staged domain knowledge files are found, returns an empty string. When files are present, the returned string starts with a header indicating user-provided domain knowledge context, followed by one markdown section per file. Each section consists of a markdown heading formed by prepending '### ' to the file's relative path, followed by the file's complete text content. Files that cannot be read due to I/O errors and files with empty content are skipped without affecting other files. The returned string has no leading or trailing whitespace beyond the content of the included files.

---

### Actual Behavior

The function returns a string and leaves no side effects. Let R = list_staged_domain_knowledge_relpaths(work_dir). If R is empty, return "". Otherwise, let project_root = os.path.dirname(os.path.abspath(work_dir)). For each r in R (in the order returned by the list function), define p = os.path.join(project_root, r). Let S be the subsequence of those r for which opening p with encoding 'utf-8', errors='replace' succeeds without raising OSError and for which f.read().strip() yields a nonempty string c_r (the stripped content of the file). Then the returned string is formed by HEADER = "User-provided domain knowledge:\nUse these Markdown notes as additional context for intended behavior, terminology, data encodings, and invariants.". If S is empty, return HEADER. Otherwise, return HEADER + "\n\n" + ( "\n\n".join( [ "### " + r + "\n" + c_r   for r in S ] ) ).

---

## Code Evidence

Line 3: relpaths = list_staged_domain_knowledge_relpaths(work_dir)

---

## Trigger Condition

The function list_staged_domain_knowledge_relpaths requires a second argument 'prefix' according to the provided context, but is called with only one argument. This will raise a TypeError, preventing any string result and violating condition B, which requires the function to return a string.

---

## How to trigger the bug

The bug claim is that `list_staged_domain_knowledge_relpaths(work_dir)` raises a `TypeError` because the function allegedly requires a second argument `prefix`. In the actual source code (`src/domain_knowledge.py`, line 109), the function signature is:

```python
def list_staged_domain_knowledge_relpaths(work_dir, prefix="fm_agent"):
```

The `prefix` parameter has a **default value** of `"fm_agent"`, making it optional. The call `list_staged_domain_knowledge_relpaths(work_dir)` with a single argument is perfectly valid and does not raise a `TypeError`. The logic verifier operated on an extracted copy of the function that omitted the caller's full signature, leading it to falsely infer that a required argument was missing.

### Inputs

| Parameter | Value |
|-----------|-------|
| work_dir | (any valid directory path, e.g. a `tempfile.TemporaryDirectory`) |

### Expected (spec-correct) Output

`""` (empty string) — when no domain knowledge files are staged in the work_dir

### Actual (buggy) Output

`""` — matches the expected output; no TypeError occurs

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
import sys, os
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "src"))
from domain_knowledge import list_staged_domain_knowledge_relpaths

with tempfile.TemporaryDirectory() as tmpdir:
    result = list_staged_domain_knowledge_relpaths(tmpdir)
    print(repr(result))
# actual (buggy) output: []  (no TypeError)
# expected (correct) output: []  (no TypeError)
```

---

## Probe Script

```python
"""Probe script for bug: list_staged_domain_knowledge_relpaths called with
only one argument (work_dir) - claimed to raise TypeError.

Bug ID: src--domain_knowledge-py--load_staged_domain_knowledge_text
"""
import sys
import tempfile
import os

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

try:
    from domain_knowledge import load_staged_domain_knowledge_text, list_staged_domain_knowledge_relpaths

    # The bug claim: list_staged_domain_knowledge_relpaths(work_dir) raises TypeError
    # because it requires a second argument 'prefix'.
    # In reality, 'prefix' has a default value "fm_agent", so the call is valid.

    with tempfile.TemporaryDirectory() as tmpdir:
        # Verify the core claim: calling with just work_dir does NOT raise TypeError
        try:
            result = list_staged_domain_knowledge_relpaths(tmpdir)
            # No TypeError raised — the bug claim is false
            actual_single_arg_ok = True
        except TypeError:
            actual_single_arg_ok = False

        # Also verify load_staged_domain_knowledge_text works end-to-end
        try:
            text_result = load_staged_domain_knowledge_text(tmpdir)
            load_ok = True
        except TypeError:
            load_ok = False

    # The spec claim says it returns a string; actual behavior matches spec
    # The bug claim was that it would raise TypeError — it doesn't
    if actual_single_arg_ok and load_ok:
        print("NOT CONFIRMED — list_staged_domain_knowledge_relpaths accepts single arg (prefix defaults to 'fm_agent'), no TypeError raised")
    else:
        print("CONFIRMED — TypeError occurred (unexpected)")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — list_staged_domain_knowledge_relpaths accepts single arg (prefix defaults to 'fm_agent'), no TypeError raised
```
