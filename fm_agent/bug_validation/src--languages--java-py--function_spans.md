# Bug Report: function_spans

**Source file:** `src/languages/java-py/function_spans.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If the codegraph backend is available and indexes the given Java file, returns a list of
    (name, start_idx, end_idx) tuples, one per function definition found in the file, ordered
    by appearance in the source. Each tuple contains the function name as a string and
    0-indexed inclusive line indices delimiting the function body.
  - If the codegraph backend is unavailable or does not index the file, returns None,
    signalling that the caller must fall back to regex-based extraction.

---

### Actual Behavior

The function returns either None or a list of (name: str, start_idx: int, end_idx: int) tuples. It returns None if the code graph backend cannot be initialised for the project directory (i.e. CodeGraphExtractor.from_proj_dir returns None) or if the Java source file is not indexed by the backend. Otherwise it returns a list where each tuple gives the function name, inclusive 0indexed start line and inclusive 0indexed end line of a function definition in the file. Formal postcondition: result = ( let cg = CodeGraphExtractor.from_proj_dir(proj_dir) ; if cg = None then None else cg.get_function_spans('java', filepath) ). Therefore (result = None)  (cg  None  result = cg.get_function_spans('java', filepath)  (result = None  (result is a list of (str, int, int) with 0  start  end and each tuple corresponds to a function definition))).

---

## Code Evidence

Line 8: return cg.get_function_spans("java", filepath) if cg else None

---

## Trigger Condition

The specification requires the list to be ordered by appearance in the source. The code delegates to cg.get_function_spans without reordering, but the backends contract does not guarantee appearance order. Therefore, an unordered result from the backend violates the specification.

---

## How to trigger the bug

The function delegates directly to `CodeGraphExtractor.get_function_spans()` without any post-hoc sorting step. When the codegraph backend returns function spans in an order that does not match source appearance order, `function_spans` passes the unordered list through unchanged, violating its spec's ordering requirement.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | any valid project directory with a `.codegraph/codegraph.db` that indexes the target file |
| `filepath` | path to a Java source file within `proj_dir` that contains two or more functions |

### Expected (spec-correct) Output

`[("func_a", 9, 19), ("func_b", 29, 39)]` — ordered by appearance (start index ascending)

### Actual (buggy) Output

`[("func_b", 29, 39), ("func_a", 9, 19)]` — reflects whatever order the backend returns, with no reordering

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import MagicMock
from src.languages.java import function_spans
from src.languages.java import CodeGraphExtractor

# Simulate a backend that returns spans out of order
orig_from_proj_dir = CodeGraphExtractor.from_proj_dir
def mock_from_proj_dir(proj_dir):
    mock_cg = MagicMock()
    mock_cg.get_function_spans.return_value = [
        ("func_b", 29, 39),
        ("func_a", 9,  19),
    ]
    return mock_cg

CodeGraphExtractor.from_proj_dir = mock_from_proj_dir
result = function_spans("/fake", "/fake/File.java")
# actual (buggy) output: [("func_b", 29, 39), ("func_a", 9, 19)]
# expected (correct) output: [("func_a", 9, 19), ("func_b", 29, 39)]
```

---

## Probe Script

```python
import sys
sys.path.insert(0, '.')
from unittest.mock import MagicMock, patch

try:
    from src.languages.java import function_spans
except Exception as e:
    print(f'ERROR: import failed: {e}')
    sys.exit(1)

# Mock CodeGraphExtractor to return UNORDERED function spans.
# func_b starts at line 30 (index 29), func_a starts at line 10 (index 9).
# If function_spans properly orders by appearance, it would return [(func_a, 9, 19), (func_b, 29, 39)].
# If it delegates without sorting (the bug), it returns the mock's order: [(func_b, 29, 39), (func_a, 9, 19)].

mock_cg = MagicMock()
mock_cg.get_function_spans.return_value = [
    ("func_b", 29, 39),  # starts later, appears first (unordered)
    ("func_a", 9,  19),  # starts earlier, appears second (unordered)
]

spec_expected = [
    ("func_a", 9,  19),  # ordered by start_idx: 9 < 29
    ("func_b", 29, 39),
]

try:
    with patch('src.languages.java.CodeGraphExtractor') as mock_extractor:
        mock_extractor.from_proj_dir.return_value = mock_cg
        actual = function_spans("/fake/proj", "/fake/File.java")
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Bug reproduced if actual matches the mock's unordered output (no sorting applied).
bug_present = actual == mock_cg.get_function_spans.return_value
spec_correct = actual == spec_expected

if bug_present:
    print(f'CONFIRMED — function_spans does NOT order by appearance.')
    print(f'  actual (unordered, matches mock):  {actual}')
    print(f'  expected (spec-ordered):           {spec_expected}')
elif spec_correct:
    print(f'NOT CONFIRMED — function_spans correctly orders by appearance.')
    print(f'  actual: {actual}')
else:
    print(f'NOT CONFIRMED — unexpected ordering.')
    print(f'  actual: {actual}')
    print(f'  expected (spec-ordered): {spec_expected}')
```

### Probe Output

```
CONFIRMED — function_spans does NOT order by appearance.
  actual (unordered, matches mock):  [('func_b', 29, 39), ('func_a', 9, 19)]
  expected (spec-ordered):           [('func_a', 9, 19), ('func_b', 29, 39)]
```
