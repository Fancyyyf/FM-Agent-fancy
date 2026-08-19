# Bug Report: batch_extract

**Source file:** `/tmp/fm_agent_wt_FM-Agent_6olacvfc/snapshot/fm_agent/extracted_functions/src/languages/rust-py/batch_extract.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When the semantic extraction backend (the codegraph index) is available for the project, returns a dict mapping the absolute path of each indexed Rust source file to the list of its extracted functions in file order; each entry is a (func_name, body) pair where func_name obeys the system-wide identity rules (canonicalized, with deterministic same-file dedup suffixes for repeated names) and body is the exact source text of that function; only Rust-language functions appear in the result. When the semantic backend is unavailable for the project, returns None (never an empty dict) so that callers record the language as having an unavailable backend and the regex fallback extraction applies to Rust files; a successfully returned empty dict instead means the backend handled the project and found no Rust functions. Per-file function lists may be empty; the dict value itself is None only in the backend-unavailable case.

---

### Actual Behavior

The function always returns a value of type dict and does not raise an exception due to a missing codegraph index. Two execution paths exist:

1. (Index found) If a codegraph index exists at proj_dir or at its immediate parent directory, CodeGraphExtractor.from_proj_dir(proj_dir) returns a valid CodeGraphExtractor instance cg. The function then returns cg.get_functions_by_file("rust", proj_dir), which is a dict mapping the absolute file path (str) of each indexed Rust source file to a list of (deduped_ident: str, body_text: str) tuples in file order. Identities follow canonicalization and per-file dedup ordering (files ordered by path then start position; first occurrence keeps the plain name, later ones receive deterministic numeric suffixes). body_text is the exact source text of the function. The per-file list may be empty for indexed files containing no Rust functions. The returned dict is never None.

2. (Index not found) If no codegraph index exists at proj_dir nor at its immediate parent directory, CodeGraphExtractor.from_proj_dir(proj_dir) returns None. The conditional expression evaluates to the else-branch and the function returns the empty dict {}.

Formal logic:
  LET idx_exists  ( index at proj_dir)  ( index at parent(proj_dir))
  LET result = batch_extract(proj_dir)
   idx_exists  result = get_functions_by_file(cg, "rust", proj_dir)  isinstance(result, dict)   k  result: isinstance(k, str)  isabs(k)  isinstance(result[k], list)   (name, body)  result[k]: isinstance(name, str)  isinstance(body, str)
   idx_exists  result = {}  isinstance(result, dict)
   In all cases: isinstance(result, dict)  result is not None
   No exception is raised solely because the codegraph index is absent.

---

## Code Evidence

Line 4: return cg.get_functions_by_file("rust", proj_dir) if cg else {}

---

## Trigger Condition

When the codegraph index is absent (cg is None), the code returns an empty dict {} via the else-branch of the conditional expression. The specification explicitly requires returning None in the backend-unavailable case, stating 'returns None (never an empty dict) so that callers record the language as having an unavailable backend and the regex fallback extraction applies to Rust files; a successfully returned empty dict instead means the backend handled the project and found no Rust functions.' Returning {} conflates 'no index found' with 'index found but no Rust functions extracted', violating the specification's contract for caller-side fallback logic.

---

## How to trigger the bug

The probe calls the Rust language handler's `batch_extract` through the public language-backend registry facade (`src.languages.registry.REGISTRY["rust"].batch_extract`), passing a fresh temporary project directory that contains no `.codegraph/codegraph.db` index (and whose immediate parent directory contains none either — the two locations checked by `CodeGraphExtractor.from_proj_dir`). Since `from_proj_dir` finds no index it returns `None`, the buggy else-branch evaluates, and the function returns the empty dict `{}`. The specification requires `None` in this backend-unavailable case so that callers (e.g. `registry.batch_extract_all`) classify the language as unavailable and apply the regex fallback.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Freshly created empty temporary directory with no `.codegraph/codegraph.db` at that directory or its immediate parent (e.g. `/tmp/fm_probe_rust_py_XXXXXX`) |

### Expected (spec-correct) Output

`None` (backend-unavailable sentinel; callers then record Rust as unavailable and fall back to regex extraction)

### Actual (buggy) Output

`{}` (empty dict — conflated with "backend handled the project but found no Rust functions")

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
import tempfile
from src.languages.registry import REGISTRY

proj_dir = tempfile.mkdtemp(prefix="fm_probe_rust_py_")  # no .codegraph index
result = REGISTRY["rust"].batch_extract(proj_dir)
print(repr(result))
# actual (buggy) output: {}
# expected (correct) output: None
```

---

## Probe Script

```py
"""Probe for bug src--languages--rust-py--batch_extract.

Spec claim: the Rust batch_extract backend must return None when the
codegraph index is unavailable (never an empty dict), so callers can record
the language as having an unavailable backend and apply the regex fallback.

Trigger: call the rust language handler's batch_extract (exposed through the
public registry facade src.languages.registry) on a project directory that
has no .codegraph/codegraph.db index. Buggy code returns {} instead of None.

FM-Agent self-validation guard: this probe only exercises the smallest unit
(the registry's rust batch_extract handler) with a fresh temporary fixture
directory; it does not start any FM-Agent workflow.
"""

import os
import sys
import tempfile

# Ensure the repo root is importable regardless of the launch directory.
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

fixture = None
try:
    from src.languages.registry import REGISTRY

    # Fresh temporary project directory owned by the probe; no files are
    # written anywhere in the active repository.
    fixture = tempfile.mkdtemp(prefix="fm_probe_rust_py_")

    # Sanity-check the trigger precondition: no codegraph index at the
    # fixture dir nor at its immediate parent (the two locations
    # CodeGraphExtractor.from_proj_dir checks).
    for candidate in (fixture, os.path.dirname(os.path.abspath(fixture))):
        index = os.path.join(candidate, ".codegraph", "codegraph.db")
        if os.path.exists(index):
            print(f"ERROR: unexpected codegraph index at {index}")
            sys.exit(1)

    rust_handler = REGISTRY["rust"]
    actual = rust_handler.batch_extract(fixture)
    expected = None  # spec: backend unavailable -> None, never {}
    passed = actual != expected  # True -> bug reproduced
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)
finally:
    if fixture and os.path.isdir(fixture):
        try:
            os.rmdir(fixture)  # fixture is an empty temp dir
        except OSError:
            pass

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: {} | expected: None
```
