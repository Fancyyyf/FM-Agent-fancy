# Bug Report: rank_functions_in_file

**Source file:** `src/scope.py` (function at line 697)
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of dicts sorted by descending score, with length at most top_k. Each dict has keys: 'file' (the filepath string), 'name' (function name string), 'lineno' (int start line), 'end_lineno' (int end line), 'score' (float rounded to 3 decimal places), and 'reason' (string). Each function name appears at most once in the result (highest-scored occurrence retained). Returns an empty list when the source file contains no localizable functions or when the file cannot be parsed.

Ranking uses heuristic signal scoring across multiple tiers: traceback function-name matches, backtick-identifier matches in function name and body, dotted Class.method reference overlap, plain identifier-name overlap, exception-type presence in the function body, and body-text word overlap with intent tokens. Scores are then propagated through the file's intra-file call graph: callees inherit a fraction of each caller's score, and callers inherit a fraction of each callee's score.

When an LLM client is provided and either (a) the top heuristic score is below llm_confidence_threshold or (b) the number of unique functions is at least llm_trigger, LLM re-ranking is attempted. If the LLM returns a ranking, those functions appear first with reason='llm', followed by top heuristic-scored functions filling remaining slots with reason='heuristic_pad'. If the LLM call produces no results or fails, the heuristic ranking is used as-is with reason='heuristic'.

---

### Actual Behavior

Natural language: After the code block executes, one of three outcomes occurs: (1) The call to `_parse_file` raises an exception, which propagates out of the block uncaught. (2) `_parse_file` returns `funcs_info` as `None` or an empty list, in which case the function `rank_functions_in_file` returns `[]`, a message `" [scope] {filepath}: no functions found, skipping"` is printed, and no further code in the block is executed. (3) `_parse_file` returns a nonempty `funcs_info` (a list of functionmetadata dicts). Then `source_lines` (list of str) and `classes` (list of class dicts or `None`) are also defined. The variable `ranked` is set to `_rank_functions(funcs_info, classes or [], signals)`, a list of dicts each containing a `score` key, sorted descending by score. A deduplication step creates `deduped_ranked`, a list containing the first entry from `ranked` for each distinct `name`, thereby keeping the highest-scored occurrence per function name while preserving the descending-score order. The dictionary `seen_names` maps each unique function name to its retained dict from `ranked`. The console output includes a separator line, a header `"FILE: {filepath}  ({len(deduped_ranked)} unique functions)"`, optionally a line listing class names if `classes` is nonempty, and a formatted header `"  rank  score  name"`. The block then falls through (the function does not return at this point); later code would continue with `deduped_ranked`, `source_lines`, and the original arguments available.

Formal logic: Let `S` be the program state immediately before the block. Input parameters `filepath`, `src_path`, `issue`, `signals`, `proj_dir`, `top_k`, `llm_client`, `llm_model`, `llm_trigger`, `llm_top_k`, `llm_confidence_threshold` are unmodified throughout the block. Let `parse_result` denote the tuple returned by `_parse_file(src_path, proj_dir=proj_dir)` in state `S`. Define three possible transitions:
1. Exception path: If `_parse_file` raises ex...

---

## Code Evidence

Line 21-40: The code block computes a preliminary ranked list and prints debug information, but never returns the required list of dicts with keys (file, name, lineno, end_lineno, score, reason). The function falls off the end and implicitly returns None, violating the specification's mandate to return a sorted list of dicts of length at most top_k.

---

## Trigger Condition

The provided code block only implements the early stages (parsing, heuristic scoring, deduplication) and does not produce the final output required by the specification. For any input file that contains at least one function, the function exits without a return statement, implicitly returning None instead of the mandated list of dicts. This is a concrete violation of the post-condition B.

---

## How to trigger the bug

The bug was assessed by calling `rank_functions_in_file` on a Python test file containing 3 functions, and checking whether the return value matches the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `filepath` | `/tmp/opencode/bug_validation_fixtures/test_module.py` |
| `src_path` | `Path("/tmp/opencode/bug_validation_fixtures/test_module.py")` |
| `issue` | `"Need to process data validation and output formatting"` |
| `signals` | `backtick_idents={'process_data','validate_input','format_output'}, all_words={'process','data','validate','input','format','output'}` (rest empty) |
| `top_k` | `2` |

### Expected (spec-correct) Output

A list of 2 dicts, each with keys `file`, `name`, `lineno`, `end_lineno`, `score`, `reason`, sorted by descending score.

### Actual (buggy) Output

The function returned a list of 2 dicts with the correct structure:

```python
[
  {'file': '/tmp/opencode/bug_validation_fixtures/test_module.py', 'name': 'validate_input', 'lineno': 10, 'end_lineno': 14, 'score': 9.342, 'reason': 'heuristic'},
  {'file': '/tmp/opencode/bug_validation_fixtures/test_module.py', 'name': 'format_output', 'lineno': 16, 'end_lineno': 18, 'score': 8.577, 'reason': 'heuristic'}
]
```

This matches the specification exactly. The actual source code at `src/scope.py` line 798 contains `return result`, which is the complete and correct return path. The bug report appears to be based on a truncated or incomplete code extract that omitted the final stages (LLM re-ranking, result construction, and return statement at lines 751-798 of the original source).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from pathlib import Path
from src.scope import rank_functions_in_file

signals = {
    'traceback_funcs': set(),
    'backtick_idents': {'test_func'},
    'dotted_refs': set(),
    'dotted_classes': set(),
    'plain_idents': set(),
    'exception_types': set(),
    'all_words': {'test', 'func'},
}

result = rank_functions_in_file(
    filepath="test.py",
    src_path=Path("test.py"),
    issue="Test issue about functions",
    signals=signals,
    top_k=5,
)
print(f"Type: {type(result)}")  # <class 'list'>
print(f"Result: {result}")       # list of dicts with correct keys
// actual (buggy) output: The function returns a properly structured list of dicts
// expected (correct) output: A list of dicts (spec is satisfied)
```

---

## Probe Script

```python
"""Probe script for bug src--scope-py--rank_functions_in_file.

Tests whether rank_functions_in_file returns a properly structured list of dicts
with keys (file, name, lineno, end_lineno, score, reason), or falls off the end
returning None.
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path so the package entry point resolves
project_root = os.path.dirname(os.path.abspath(__file__))
# The project root is the workspace root
repo_root = os.environ.get("FM_AGENT_REPO_ROOT", os.getcwd())

# We need the repo root in sys.path so that config, src package resolve
for p in [repo_root, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from src.scope import rank_functions_in_file

    # Create a temp test fixtures directory
    fixtures_dir = Path("/tmp/opencode/bug_validation_fixtures")
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    test_file = fixtures_dir / "test_module.py"

    # Parse signals matching the expected structure
    signals: dict[str, set[str]] = {
        'traceback_funcs': set(),
        'backtick_idents': {'process_data', 'validate_input', 'format_output'},
        'dotted_refs':     set(),
        'dotted_classes':  set(),
        'plain_idents':    set(),
        'exception_types': set(),
        'all_words':       {'process', 'data', 'validate', 'input', 'format', 'output'},
    }

    result = rank_functions_in_file(
        filepath=str(test_file),
        src_path=test_file,
        issue="Need to process data validation and output formatting",
        signals=signals,
        top_k=2,
    )

    # Verify the spec claims
    spec_required_keys = {'file', 'name', 'lineno', 'end_lineno', 'score', 'reason'}

    if result is None:
        print("CONFIRMED — rank_functions_in_file returned None (spec requires list of dicts)")
    elif not isinstance(result, list):
        print(f"CONFIRMED — rank_functions_in_file returned {type(result).__name__} instead of list")
    elif len(result) > 2:
        print(f"CONFIRMED — result length {len(result)} > top_k=2 (spec requires length ≤ top_k)")
    else:
        # Check each entry has all required keys
        missing_keys = False
        wrong_types = False
        for i, entry in enumerate(result):
            if not isinstance(entry, dict):
                wrong_types = True
                print(f"CONFIRMED — entry[{i}] is not a dict")
                break
            for key in spec_required_keys:
                if key not in entry:
                    missing_keys = True
                    print(f"CONFIRMED — entry[{i}] missing key '{key}'")
                    break
            if missing_keys or wrong_types:
                break

        if not missing_keys and not wrong_types:
            # Verify scores are sorted descending
            scores = [e['score'] for e in result]
            is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
            if not is_sorted:
                print(f"CONFIRMED — scores not sorted descending: {scores}")
            else:
                print(
                    f"NOT CONFIRMED — rank_functions_in_file returned valid list of "
                    f"{len(result)} dict(s) with correct keys, scores sorted descending. "
                    f"The function correctly returns result (line 798 of src/scope.py)."
                )
                sys.exit(0)

except ImportError as e:
    print(f"ERROR: Could not import src.scope: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
──────────────────────────────────────────────────────────────────────
FILE: /tmp/opencode/bug_validation_fixtures/test_module.py  (3 unique functions)
  rank     score  name
  ----   -------  ----
     1     9.342  validate_input  (L10-14)  <<
     2     8.577  format_output  (L16-18)  <<
     3     6.908  process_data  (L3-8)
  → selected (heuristic): validate_input (9.342), format_output (8.577)
NOT CONFIRMED — rank_functions_in_file returned valid list of 2 dict(s) with correct keys, scores sorted descending. The function correctly returns result (line 798 of src/scope.py).
```
