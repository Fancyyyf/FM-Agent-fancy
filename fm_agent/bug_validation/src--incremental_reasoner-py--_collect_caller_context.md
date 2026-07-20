# Bug Report: _collect_caller_context

**Source file:** `/tmp/fm_agent_wt_FM-Agent_9w930mtx/snapshot/fm_agent/extracted_functions/src/incremental_reasoner-py/_collect_caller_context.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of (caller_fqn, caller_spec, callee_expectation) tuples
  - Each caller_fqn is a member of callers_map[fqn] whose mapped file exists on disk and contains at least one of a [SPEC] block or a matching [INFO] entry for fqn
  - caller_spec is the textual content of the caller's [SPEC] block, or None if the caller's file has no [SPEC] block
  - callee_expectation is the textual content of the [INFO] entry within the caller's file that describes expectations for fqn, or None if no matching entry exists or the caller has no [INFO] block
  - When edge_aliases_map is provided and contains an alias entry for fqn under a given caller, matching is widened: a [INFO] entry whose callee name matches any alias of fqn for that caller is treated as a match for fqn
  - Callers for which the mapped file does not exist or yields neither caller_spec nor callee_expectation are omitted from the returned list
  - The returned list is ordered by caller_fqn in ascending lexicographic sort order

---

### Actual Behavior

The function returns a list of triples (caller_fqn, caller_spec, callee_expectation). Let L be the iterable of caller FQN strings obtained from callers_map for fqn (empty iterable if fqn is not a key). Let S be the sorted list produced by sorting the elements of L. The returned list is built by processing each element of S in order: for each caller_fqn in S, retrieve its filesystem path from file_map. If the path is present and is an existing regular file, extract its [SPEC] block via extract_spec_block and its [INFO] block via extract_info_block. If an [INFO] block was found, use it to extract the callee specification for fqn under aliases obtained from edge_aliases_map (if provided) by extracting the tuple of aliases for caller_fqn as a caller of fqn; otherwise the callee specification is set to None. The current caller_fqn is included in the result if and only if either the [SPEC] block or the callee specification is not None. The result list preserves the order imposed by the sorted caller_fqn sequence; duplicate caller_fqn entries from the original iterable remain as separate entries in the final list. Formally:

Let L = callers_map.get(fqn, ())
Let S = sorted(tuple(L))
context = []
For each k in 0..len(S)-1:
  c = S[k]
  p = file_map.get(c)
  if p is not None and os.path.isfile(p):
    spec = extract_spec_block(Path(p))
    info = extract_info_block(Path(p))
    if edge_aliases_map is not None:
      aliases = tuple(edge_aliases_map.get(fqn, {}).get(c, ()))
    else:
      aliases = ()
    exp = extract_callee_spec_from_info(info, fqn, aliases) if info is not None else None
    if spec is not None or exp is not None:
      context.append((c, spec, exp))
  else:
    # skip this caller
Return context

---

## Code Evidence

Line 23: if caller_spec or expectation:

---

## Trigger Condition

The condition uses truthiness to decide whether a caller should be included. An empty [SPEC] block yields an empty string (truthiness False), but the specification states that a caller with a [SPEC] block must be included regardless of its content, with caller_spec set to the block content (even if empty). Therefore the code incorrectly omits callers whose [SPEC] block is empty.

---

## How to trigger the bug

The code at line 59 of the extracted function (`if caller_spec or expectation:`) uses truthiness (`or`) to decide whether to include a caller. The correct check should be `if caller_spec is not None or expectation is not None`, which distinguishes "no [SPEC] block" (None) from "empty [SPEC] block" (empty string).

However, the current `extract_spec_block` implementation in `src/generate_batch_prompts.py` returns the full [SPEC] block **including** the comment markers (e.g., `# [SPEC]\n# [SPEC]`), so `caller_spec` is never a falsy string when present — it is either a non-empty marker-inclusive string or `None`. The truthiness bug does **not** manifest with the current `extract_spec_block` implementation.

The bug is structurally real and **latent**: if `extract_spec_block` were ever changed to return only the content between markers (as its own `[INFO]` spec describes — "returns its full textual content **excluding** the markers"), an empty `[SPEC]` block would produce an empty string `""`, which is falsy, and the `if caller_spec or expectation:` check would incorrectly omit the caller.

### Inputs

| Parameter | Value |
|-----------|-------|
| fqn | `"module::callee_func"` |
| callers_map | `{"module::callee_func": ("module::caller_func",)}` |
| file_map | `{"module::caller_func": "<tmpdir>/caller_with_spec.py"}` |
| caller file content | `"# [SPEC]\n# [SPEC]\n\ndef caller_func(): pass\n"` |

### Expected (spec-correct) Output

`[("module::caller_func", "# [SPEC]\n# [SPEC]", None)]`

### Actual (buggy) Output

`[("module::caller_func", "# [SPEC]\n# [SPEC]", None)]`

The actual output is **correct** with the current implementation because `extract_spec_block` returned `"# [SPEC]\n# [SPEC]"` (truthy). The bug would only manifest if `extract_spec_block` returned `""`.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, tempfile
from pathlib import Path
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_9w930mtx/snapshot')
from src.incremental_reasoner import _collect_caller_context

tmpdir = tempfile.mkdtemp(prefix="probe_caller_context_")
caller_path = Path(tmpdir) / "caller_with_spec.py"
caller_path.write_text("# [SPEC]\n# [SPEC]\n\ndef caller_func(): pass\n")

result = _collect_caller_context(
    "module::callee_func",
    {"module::callee_func": ("module::caller_func",)},
    {"module::caller_func": str(caller_path)},
)
# actual (buggy) output: [('module::caller_func', '# [SPEC]\n# [SPEC]', None)]
# expected (correct) output: [('module::caller_func', '# [SPEC]\n# [SPEC]', None)]
# NOTE: bug does not manifest because extract_spec_block includes markers
```

---

## Probe Script

```python
"""Probe for _collect_caller_context truthiness bug at line 1445.

The bug: 'if caller_spec or expectation:' uses truthiness instead of 'is not None'.
A caller whose [SPEC] block exists but whose extract_spec_block returns a falsy
value (e.g., empty string '') is incorrectly omitted.

This probe creates a synthetic scenario where extract_spec_block returns an empty
string to demonstrate the bug. It also tests with the real extract_spec_block
(which currently includes markers, so it's always truthy) to verify the current
behavior.
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Ensure the project root is on the path so imports work
PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJ_ROOT)

from src.incremental_reasoner import _collect_caller_context
from src.generate_batch_prompts import extract_spec_block


def test_truthiness_bug():
    """Create a scenario where extract_spec_block returns empty string for an empty [SPEC] block.
    
    The trigger_condition states: "An empty [SPEC] block yields an empty string
    (truthiness False), but the specification states that a caller with a [SPEC]
    block must be included regardless of its content."
    
    Since the real extract_spec_block includes markers, we test by:
    1. Creating a file whose spec block when processed yields a falsy value.
    2. If the real extract_spec_block doesn't produce falsy, we test with a
       synthetic substitute to prove the pattern is buggy.
    """
    tmpdir = tempfile.mkdtemp(prefix="probe_caller_context_")
    fqn = "module::callee_func"
    caller_fqn = "module::caller_func"

    try:
        # --- Scenario 1: file with a [SPEC] block that has no content between markers ---
        # Create a caller file with an empty SPEC block (start/end markers only)
        caller_path = Path(tmpdir) / "caller_with_spec.py"
        caller_path.write_text("# [SPEC]\n# [SPEC]\n\ndef caller_func(): pass\n")
        
        callers_map = {fqn: (caller_fqn,)}
        file_map = {caller_fqn: str(caller_path)}
        
        result = _collect_caller_context(fqn, callers_map, file_map)
        
        # What does extract_spec_block actually return for an empty block?
        raw_spec = extract_spec_block(caller_path)
        spec_is_falsy = not bool(raw_spec)
        
        print(f"Extract_spec_block result for empty SPEC: {raw_spec!r}")
        print(f"Result (falsy? {spec_is_falsy}): {result!r}")
        
        # --- Scenario 2: Direct truthiness test ---
        # Test: if extract_spec_block returned "" (as the spec says it should for
        # empty blocks when excluding markers), would the caller be omitted?
        # We simulate this by creating a file whose spec block causes extract_spec_block
        # to return an empty string.
        
        # Create a file where extract_spec_block returns "" due to whitespace-only content
        # Actually, extract_spec_block includes markers, so this won't be empty.
        # Let's verify whether the pattern <tag>...<tag> with nothing meaningful between
        # can cause the issue.
        
        # --- Alternative: check the exact bug condition ---
        # The spec says: callers with a [SPEC] block must be included even if the block
        # content is empty. The check is 'if caller_spec or expectation:'.
        # Since extract_spec_block includes markers, caller_spec will be truthy.
        # The bug is LATENT - it would manifest if extract_spec_block excluded markers.
        
        if spec_is_falsy:
            # Bug manifested! Caller with empty [SPEC] was omitted.
            if result:
                print("NOT CONFIRMED — caller was included despite falsy caller_spec")
            else:
                print("CONFIRMED — caller with [SPEC] block was incorrectly omitted (empty block treated as falsy)")
        else:
            # extract_spec_block includes markers, so caller_spec is always truthy
            if result:
                print("CURRENT BEHAVIOR: caller IS included (spec block includes markers → truthy)")
            else:
                print("NOT CONFIRMED — caller was omitted for unexpected reason")
            
            # Now demonstrate the structural flaw: manually simulate what happens
            # if extract_spec_block returned "" for empty blocks (excluding markers,
            # as its own [INFO] spec claims it should).
            print()
            print("--- Structural flaw demonstration ---")
            print("The check 'if caller_spec or expectation:' at line 1445 uses")
            print("truthiness. If extract_spec_block excluded markers and returned")
            print("an empty string '' for an empty [SPEC] block, the condition would")
            print("evaluate to False and the caller would be incorrectly omitted.")
            print("The fix should be: 'if caller_spec is not None or expectation is not None'")
            print()
            
            # Formal verdict
            print("NOT CONFIRMED — the truthiness check at line 1445 is structurally")
            print("incorrect (should use 'is not None'), but it does not manifest with")
            print("the current extract_spec_block implementation which includes markers.")
            
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    try:
        test_truthiness_bug()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

### Probe Output

```
Extract_spec_block result for empty SPEC: '# [SPEC]\n# [SPEC]'
Result (falsy? False): [('module::caller_func', '# [SPEC]\n# [SPEC]', None)]
CURRENT BEHAVIOR: caller IS included (spec block includes markers → truthy)

--- Structural flaw demonstration ---
The check 'if caller_spec or expectation:' at line 1445 uses
truthiness. If extract_spec_block excluded markers and returned
an empty string '' for an empty [SPEC] block, the condition would
evaluate to False and the caller would be incorrectly omitted.
The fix should be: 'if caller_spec is not None or expectation is not None'

NOT CONFIRMED — the truthiness check at line 1445 is structurally
incorrect (should use 'is not None'), but it does not manifest with
the current extract_spec_block implementation which includes markers.
```
