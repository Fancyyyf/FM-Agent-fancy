# Bug Report: rank_functions_in_file

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/scope-py/rank_functions_in_file.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If the file contains zero parseable functions, returns an empty list.
- Otherwise, returns a list of dicts sorted in descending order by 'score'.
- Each returned dict contains the keys: 'file' (str, equal to filepath),
  'name' (str), 'lineno' (int, 1based start line), 'end_lineno' (int,
  1based end line), 'score' (float, rounded to 3 decimal places), and
  'reason' (str, one of "heuristic", "llm", "heuristic_pad").
- The returned list length is at most top_k.
- Every 'name' in the result is unique; if a name appeared in multiple
  positions within the file, only the occurrence with the highest score is kept.
- Every 'name' in the result corresponds to a function actually defined
  in the source file.
- Scores reflect relevance to the issue as judged against the signals.
- When an LLM client is provided AND EITHER the highest heuristic score among
  all unique functions is below llm_confidence_threshold OR the count of
  unique functions in the file is at least llm_trigger, LLMbased reranking
  is attempted. On success, entries chosen by the LLM carry reason="llm"
  and remaining heuristic fillers up to top_k carry reason="heuristic_pad".
- When LLM reranking is not attempted or fails, all returned entries carry
  reason="heuristic".

---

### Actual Behavior

If _parse_file returns funcs_info that is None or empty, the function prints the message and returns the empty list []. Otherwise, funcs_info is non-empty, _rank_functions computes a scored list, deduplication by name produces deduped_ranked, and the function prints a formatted table header; after printing it reaches the end of the block and returns None (implicit return). The arguments filepath, src_path, issue, signals, top_k, llm_client, llm_model, llm_trigger, llm_top_k, llm_confidence_threshold, proj_dir are unchanged. No exceptions are raised under the given pre-conditions. Stdout receives the relevant output lines.

---

## Code Evidence

After Line 40, the function lacks an explicit return statement, so it returns None implicitly.

---

## Trigger Condition

The specification requires returning a list of dicts when there are parseable functions, but the code returns None for any input that produces a nonempty funcs_info because no return is executed after printing.

---

## How to trigger the bug

The bug claim states that `rank_functions_in_file` returns `None` because it "lacks an explicit return statement after line 40." In the actual source code at `src/scope.py`, the function body ends with `return result` at line 798, correctly returning a `list[dict]`. The probe script confirms this: calling the function with a parseable Python file returns a properly structured list of dicts, not `None`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `filepath` | `'test_file.py'` |
| `src_path` | `Path(tmp.name)` (temp file containing `def hello(): return 'world'`) |
| `issue` | `'test issue about hello'` |
| `signals` | `{'traceback_funcs': set(), 'backtick_idents': set(), 'dotted_refs': set(), 'dotted_classes': set(), 'plain_idents': {'hello'}, 'exception_types': set(), 'all_words': {'hello'}}` |
| `top_k` | `5` |

### Expected (spec-correct) Output

A list of dicts, e.g. `[{'file': 'test_file.py', 'name': 'hello', 'lineno': 1, 'end_lineno': 2, 'score': 5.207, 'reason': 'heuristic'}]`

### Actual (buggy) Output

A list of dicts: `[{'file': 'test_file.py', 'name': 'hello', 'lineno': 1, 'end_lineno': 2, 'score': 5.207, 'reason': 'heuristic'}]` — matches the expected spec-compliant output. No bug present.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, '.')
from src.scope import rank_functions_in_file

tmp = tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False)
tmp.write("def hello():\n    return 'world'\n")
tmp.close()

result = rank_functions_in_file(
    filepath='test_file.py',
    src_path=Path(tmp.name),
    issue='test issue about hello',
    signals={'traceback_funcs': set(), 'backtick_idents': set(),
             'dotted_refs': set(), 'dotted_classes': set(),
             'plain_idents': {'hello'}, 'exception_types': set(),
             'all_words': {'hello'}},
    top_k=5,
)
# actual (buggy) output: [{'file': 'test_file.py', 'name': 'hello', ...}] (a list)
# expected (correct) output: [{'file': 'test_file.py', 'name': 'hello', ...}] (a list)
print(result)
```

---

## Probe Script

```python
import sys
import os
import tempfile
from pathlib import Path

# Add snapshot root to sys.path so `from src.scope import ...` resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.scope import rank_functions_in_file

    # Create a temporary Python file with a simple parseable function
    tmp = tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False)
    tmp.write("def hello():\n    return 'world'\n")
    tmp.close()
    src_path = Path(tmp.name)

    # Build minimal signals dict (all keys required by the spec)
    signals = {
        'traceback_funcs': set(),
        'backtick_idents': set(),
        'dotted_refs': set(),
        'dotted_classes': set(),
        'plain_idents': {'hello'},
        'exception_types': set(),
        'all_words': {'hello'},
    }

    actual = rank_functions_in_file(
        filepath='test_file.py',
        src_path=src_path,
        issue='test issue about hello',
        signals=signals,
        top_k=5,
    )

    # Spec requires a list of dicts. Bug claims code returns None instead.
    expected_type = list
    passed = not isinstance(actual, expected_type)  # True → bug reproduced

    if passed:
        print(f'CONFIRMED — actual: {type(actual).__name__} ({actual!r}) | expected: list')
    else:
        print(f'NOT CONFIRMED — actual matched expected type list: {actual!r}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    try:
        os.unlink(tmp.name)
    except (NameError, OSError):
        pass
```

### Probe Output

```
──────────────────────────────────────────────────────────────────────
FILE: test_file.py  (1 unique functions)
  rank     score  name
  ----   -------  ----
     1     5.207  hello  (L1-2)  <<
  → selected (heuristic): hello (5.207)
NOT CONFIRMED — actual matched expected type list: [{'file': 'test_file.py', 'name': 'hello', 'lineno': 1, 'end_lineno': 2, 'score': 5.207, 'reason': 'heuristic'}]
```
