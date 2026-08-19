# Bug Report: function_id_from_extracted_path

**Source file:** `fm_agent/extracted_functions/src/opencode_trace-py/function_id_from_extracted_path.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a string that is the canonical fully-qualified function name (FQN) for the function whose extracted body resides at the given path. The FQN is derived by: removing any leading extracted-functions directory prefix (the longest matching prefix among 'fm_agent/extracted_functions/' and 'extracted_functions/') from a normalized form of the path; stripping the file extension; and replacing all remaining path-component separators with '::' (double colon). The returned string contains no file extension and uniquely identifies a function within the project's FQN namespace.

---

### Actual Behavior

The function returns a string derived from the input `path` by applying the following transformations: (1) replace all backslashes with forward slashes; (2) if the resulting string starts with 'fm_agent/extracted_functions/', remove that prefix; otherwise, if it starts with 'extracted_functions/', remove that prefix; (3) remove the file extension (the part from the last '.' onward, including the dot) via os.path.splitext, keeping only the root; (4) replace all forward slashes with '::'. Formally, let s = path.replace('\\', '/'); let t = s[30:] if s.startswith('fm_agent/extracted_functions/') else (s[21:] if s.startswith('extracted_functions/') else s); then the returned value R(path) = os.path.splitext(t)[0].replace('/', '::'). The transformation is deterministic and does not raise exceptions for any nonempty string input.

---

## Code Evidence

```
def function_id_from_extracted_path(path):
    rel = path.replace("\\", "/")                      # Line 2 — only backslash → forward slash, no collapse
    for prefix in ("fm_agent/extracted_functions/", "extracted_functions/"):
        if rel.startswith(prefix):
            rel = rel[len(prefix):]
            break
    return os.path.splitext(rel)[0].replace("/", "::")
```

The critical omission is on line 2: `path.replace("\\", "/")` does **not** collapse consecutive forward slashes (e.g., `//` → `/`). The specification requires the path to be _normalized_ before prefix removal, and normalization in typical path-handling libraries includes collapsing redundant separators. Because the code skips this step, paths with consecutive slashes produce incorrect FQN values containing repeated `::` separators.

---

## Trigger Condition

The specification requires removing the prefix from a normalized form of the path, and then replacing path-component separators with '::'. Normalization typically includes collapsing consecutive separators. The code only replaces backslashes (Line 2) and does not collapse multiple slashes. For 'extracted_functions/foo//bar.py', the code returns 'foo::::bar', whereas the normalized form yields 'foo::bar'.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `path` (test 1) | `'extracted_functions/foo//bar.py'` |
| `path` (test 2) | `'extracted_functions//foo/bar.py'` |
| `path` (test 3) | `'extracted_functions/foo///bar.py'` |

### Expected (spec-correct) Output

For all three inputs, after normalization (collapse consecutive slashes), prefix removal, extension stripping, and `::` replacement:

`'foo::bar'`

### Actual (buggy) Output

| Input | Actual Output |
|-------|---------------|
| `'extracted_functions/foo//bar.py'` | `'foo::::bar'` |
| `'extracted_functions//foo/bar.py'` | `'::foo::bar'` |
| `'extracted_functions/foo///bar.py'` | `'foo::::::bar'` |

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')
from src.opencode_trace import function_id_from_extracted_path

# Normalization bug: consecutive slashes not collapsed
print(function_id_from_extracted_path('extracted_functions/foo//bar.py'))
# actual (buggy) output: 'foo::::bar'
# expected (correct) output: 'foo::bar'
```

---

## Probe Script

```python
import sys
import os

# Add repo root to path so we can import src.opencode_trace
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.opencode_trace import function_id_from_extracted_path
    
    # Trigger condition: path with consecutive slashes
    # The spec says normalization should happen before path-separator replacement.
    # Normalization includes collapsing consecutive separators.
    # The code does NOT collapse multiple slashes.
    
    # Test 1: double slash in path
    input_path = "extracted_functions/foo//bar.py"
    actual = function_id_from_extracted_path(input_path)
    # If normalized correctly (collapsing slashes THEN replacing), we'd get "foo::bar"
    # The buggy code returns "foo::::bar" (double slashes become double colons)
    expected = "foo::bar"
    passed = actual != expected  # True means bug confirmed
    
    # Collect additional evidence
    evidence = []
    evidence.append(f"Test path: {input_path!r}")
    evidence.append(f"Actual:   {actual!r}")
    evidence.append(f"Expected: {expected!r}")
    
    # Test 2: another variant with leading double slash
    input_path2 = "extracted_functions//foo/bar.py"
    actual2 = function_id_from_extracted_path(input_path2)
    expected2 = "foo::bar"
    if actual2 != expected2:
        evidence.append(f"")
        evidence.append(f"Test path: {input_path2!r}")
        evidence.append(f"Actual:   {actual2!r}")
        evidence.append(f"Expected: {expected2!r}")
    
    # Test 3: triple slash
    input_path3 = "extracted_functions/foo///bar.py"
    actual3 = function_id_from_extracted_path(input_path3)
    expected3 = "foo::bar"
    if actual3 != expected3:
        evidence.append(f"")
        evidence.append(f"Test path: {input_path3!r}")
        evidence.append(f"Actual:   {actual3!r}")
        evidence.append(f"Expected: {expected3!r}")
    
    if passed:
        print("CONFIRMED — actual differs from normalized expected output:")
        for line in evidence:
            print("  " + line)
    else:
        print("NOT CONFIRMED — actual matched normalized expected:", actual)
        
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual differs from normalized expected output:
  Test path: 'extracted_functions/foo//bar.py'
  Actual:   'foo::::bar'
  Expected: 'foo::bar'
  
  Test path: 'extracted_functions//foo/bar.py'
  Actual:   '::foo::bar'
  Expected: 'foo::bar'
  
  Test path: 'extracted_functions/foo///bar.py'
  Actual:   'foo::::::bar'
  Expected: 'foo::bar'
```
