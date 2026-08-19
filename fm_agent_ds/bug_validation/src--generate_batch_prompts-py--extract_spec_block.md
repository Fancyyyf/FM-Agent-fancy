# Bug Report: extract_spec_block

**Source file:** `fm_agent/extracted_functions/src/generate_batch_prompts-py/extract_spec_block.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a formatted string composed from the 'signature', 'pre_condition', and 'post_condition' fields of the adjacent .spec.json sidecar when that sidecar exists, parses to a JSON dict, and contains all three of those keys with string values. The returned string follows the form '<signature>\n\nPre-condition:\n<pre_condition>\n\nPost-condition:\n<post_condition>'. Returns None when the sidecar does not exist, cannot be opened or read as UTF-8 text, contains syntactically invalid JSON, parses to a non-dict JSON value, or lacks any of the three required keys with string values.

---

### Actual Behavior

The function returns None if any of the following occur: (1) an OSError, UnicodeDecodeError, or json.JSONDecodeError is raised during the attempt to open, read, or parse the file at the path obtained by _spec_json_path(filepath) (which appends '.spec.json' to filepath); (2) the parsed JSON value is not an instance of dict. Otherwise, the function returns the string: f"{spec.get('signature', '')}\n\nPre-condition:\n{spec.get('pre_condition', '')}\n\nPost-condition:\n{spec.get('post_condition', '')}", where spec is the dict obtained from parsing the file. Any other exception propagates. Formal: (return_value = None)  ( spec: isinstance(spec, dict)  return_value = spec.get('signature', '') + '\n\nPre-condition:\n' + spec.get('pre_condition', '') + '\n\nPost-condition:\n' + spec.get('post_condition', '')  valid_file_and_spec(_spec_json_path(filepath), spec)).

---

## Code Evidence

Line 11: return (

---

## Trigger Condition

The specification requires returning None when any of the three keys ('signature', 'pre_condition', 'post_condition') has a non-string value (e.g., integer 42), but the code ignores value types and returns a formatted string instead.

---

## How to trigger the bug

The function `extract_spec_block(filepath)` reads a `.spec.json` sidecar file, parses it, and returns a formatted string. The specification requires that if any of the three keys (`signature`, `pre_condition`, `post_condition`) has a **non-string** value, the function must return `None`. However, the implementation uses `spec.get(key, '')` for all three, which only handles **missing** keys — it does not check the **type** of the existing values. Any non-string value (e.g., integer, list, boolean) is silently converted to string via f-string interpolation.

### Inputs

| Parameter | Value |
|-----------|-------|
| `filepath` | `Path("...temp.../test.py")` — points to a file whose adjacent `.spec.json` contains: |
| `.spec.json` content | `{"signature": "my_func(int x) -> int", "pre_condition": 42, "post_condition": "returns x + 1"}` |

### Expected (spec-correct) Output

`None`

### Actual (buggy) Output

`'my_func(int x) -> int\n\nPre-condition:\n42\n\nPost-condition:\nreturns x + 1'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json
import tempfile
from pathlib import Path
from src.generate_batch_prompts import extract_spec_block

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)
    spec = {"signature": "my_func(int x) -> int", "pre_condition": 42, "post_condition": "returns x + 1"}
    (tmp / "test.py.spec.json").write_text(json.dumps(spec))
    result = extract_spec_block(tmp / "test.py")
    # actual (buggy) output: 'my_func(int x) -> int\n\nPre-condition:\n42\n\nPost-condition:\nreturns x + 1'
    # expected (correct) output: None
```

---

## Probe Script

```python
"""Probe script for bug: src--generate_batch_prompts-py--extract_spec_block.

Bug: extract_spec_block() does not return None when spec keys have non-string values.
Spec requires: return None when any of signature/pre_condition/post_condition has a non-string value.
Actual: always returns formatted string using spec.get() without type-checking values.
"""

import json
import sys
import tempfile
from pathlib import Path

# Load the package via its public entry point
from src.generate_batch_prompts import extract_spec_block


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Create a .spec.json with all three keys but one has a non-string value (integer)
        spec_content = {
            "signature": "my_func(int x) -> int",
            "pre_condition": 42,           # Non-string value — spec says this should cause None
            "post_condition": "returns x + 1",
        }

        test_file = tmp / "test.py"
        spec_file = tmp / "test.py.spec.json"

        spec_file.write_text(json.dumps(spec_content))

        try:
            actual = extract_spec_block(test_file)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)

        # Spec claims: return None when any key has a non-string value
        # Actual code: returns formatted string regardless of value types
        expected = None
        passed = actual is not None  # True = bug reproduced (returned string instead of None)

        if passed:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
            print(f"(Returned a string when spec requires None for non-string values)")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — actual: 'my_func(int x) -> int\n\nPre-condition:\n42\n\nPost-condition:\nreturns x + 1' | expected: None
(Returned a string when spec requires None for non-string values)
```
