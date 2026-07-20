# Bug Report: function_id_from_extracted_path

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/opencode_trace-py/function_id_from_extracted_path.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the fully-qualified function name (FQN) derived from path
- If path begins with the prefix "fm_agent/extracted_functions/" or "extracted_functions/" (after normalizing backslashes to "/"), that prefix is removed before deriving the FQN; otherwise the prefix portion of the path is retained as-is
- The FQN is formed by: stripping the last file extension (the shortest suffix beginning with the final "." in the filename) from the path, then replacing every remaining "/" separator with "::"
- The returned string contains no "/" or "\\" characters and no final file extension

---

### Actual Behavior

The function returns a string formed by applying the following transformations in sequence: 1) replace every '\\' with '/' in the input path; 2) if the resulting string starts with 'fm_agent/extracted_functions/', remove that prefix; otherwise, if it starts with 'extracted_functions/', remove that prefix; 3) remove the file extension using os.path.splitext (i.e., remove the substring from the last '.' that follows a non-leading position in the final path component to the end, respecting that a single leading dot in the basename is treated as part of the name and not as an extension separator); 4) replace every remaining '/' with '::'. Formally: let s0 = path.replace('\\', '/'); let prefix1 = 'fm_agent/extracted_functions/', prefix2 = 'extracted_functions/'; if s0 starts with prefix1 then s1 = s0[29:] else if s0 starts with prefix2 then s1 = s0[20:] else s1 = s0; let (base, _) = os.path.splitext(s1); return base.replace('/', '::').

---

## Code Evidence

Line 7: return os.path.splitext(rel)[0].replace("/", "::")

---

## Trigger Condition

The specification requires stripping the last file extension, defined as the shortest suffix beginning with the final '.' in the filename. For a filename like '.hidden', the final '.' is the leading dot, so the suffix to strip is '.hidden' itself, leaving an empty basename. The code uses os.path.splitext, which treats leading dots in the basename as part of the name and returns ('.hidden', ''). Therefore, the code incorrectly retains the leading dot, violating the specification.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| path | `"extracted_functions/src/.hidden"` |

### Expected (spec-correct) Output

`"src::"`

### Actual (buggy) Output

`"src::.hidden"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.opencode_trace import function_id_from_extracted_path

result = function_id_from_extracted_path("extracted_functions/src/.hidden")
print(result)
# actual (buggy) output: 'src::.hidden'
# expected (correct) output: 'src::'
```

---

## Probe Script

```python
import sys
try:
    from src.opencode_trace import function_id_from_extracted_path

    # Per spec: extension is "the shortest suffix beginning with the final '.' in the filename".
    # For '.hidden', the final '.' is at position 0 of the basename, so the extension is '.hidden'
    # and the basename should be empty.
    # os.path.splitext('.hidden') returns ('.hidden', '') — retaining the leading dot as part of the name.
    actual   = function_id_from_extracted_path("extracted_functions/src/.hidden")
    expected = "src::"

    passed   = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: 'src::.hidden' | expected: 'src::'
```
