# Bug Report: _codegraph_functions_by_file

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/_codegraph_functions_by_file.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dict mapping each normalized relative file path string to a dict of {function_identifier: function_source_text} for all files under proj_dir whose language matches any key in lang_keys and whose functions are indexed by CodeGraph. Function identifiers use class-qualified names for C++ methods. If no usable CodeGraph index is available at proj_dir, returns None.

---

### Actual Behavior

If `CodeGraphExtractor.from_proj_dir(proj_dir)` returns `None`, the function returns `None`. Otherwise, it returns a dictionary `result` that maps normalized relative file paths (strings like `'path/to/file.py'`) to dictionaries of function identifiers to source code strings. The mapping is built by iterating over `lang_key` in `sorted(lang_keys)` (lexicographic order), obtaining for each the mapping from absolute paths to function dicts via `extractor.get_functions_by_file(lang_key, proj_dir)`, and for each absolute path `a` and function dict `fd` in that mapping, updating `result[_normalized_relative_path(proj_dir, a)] = dict(fd)`. Because later language keys overwrite earlier ones, the final value for a relative path corresponds to the last language key (in sorted order) that contains that absolute path. If no functions are present for any language key, `result` is an empty dictionary. Formal: Let `E = CodeGraphExtractor.from_proj_dir(proj_dir)`. If `E = None`, return value is `None`. Otherwise, let `S = sorted(lang_keys)`. Initial `R = {}`. For each `lk  S`, for each `(a, fd)  E.get_functions_by_file(lk, proj_dir).items()`, assign `R[_normalized_relative_path(proj_dir, a)] = fd`. The final return value is `R`. Thus, `R` satisfies: `dom(R) = { _normalized_relative_path(proj_dir, a) |  lk  S, a  dom(E.get_functions_by_file(lk, proj_dir)) }` and for each `p  dom(R)`, `R[p] = E.get_functions_by_file(l, proj_dir)[a]` where `l = max{ lk  S |  a: _normalized_relative_path(proj_dir, a) = p  a  dom(E.get_functions_by_file(lk, proj_dir)) }`, and `a` is some absolute path that normalizes to `p` for that `l`.

---

## Code Evidence

```
Line 12: for abs_path, functions in extractor.get_functions_by_file(
Line 13: lang_key, proj_dir
Line 14: ).items():
```

---

## Trigger Condition

The specification requires returning a dict mapping files matching any key in lang_keys, or None if no index. When lang_keys contains an unrecognized key, get_functions_by_file may raise an exception due to its precondition (lang_key recognized), causing the function to propagate the exception instead of returning a dict or None. This violates the specification.

---

## How to trigger the bug

The bug could not be confirmed. `CodeGraphExtractor.get_functions_by_file` handles unrecognized language keys gracefully: at line 273-275 of `src/languages/codegraph.py`, it checks `cg_langs = _CG_LANG.get(lang_key)` and returns `{}` when the key is not found. No exception is raised. The caller `_codegraph_functions_by_file` iterates over the empty dict's `.items()` (which yields nothing), and returns an empty dict `{}`. This is consistent with the specification, which requires returning a dict mapping files whose language matches any key in `lang_keys` — an unrecognized key matches no files.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `/home/fancy/Projects_Vault/FM-Agent` |
| `lang_keys` | `["nonexistent_lang_key"]` |

### Expected (spec-correct) Output

`{}` (empty dict — no file language matches an unrecognized key)

### Actual (buggy) Output

`{}` (empty dict — no exception raised)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.codegraph import CodeGraphExtractor
from src.incremental_reasoner import _codegraph_functions_by_file

# Bug claim: unrecognized lang_key causes exception.
# Reality: it returns {} — no exception.
result = _codegraph_functions_by_file("/home/fancy/Projects_Vault/FM-Agent", ["nonexistent_lang_key"])
# actual (buggy) output: {} (empty dict)
# expected (correct) output: {} (empty dict)
print(result)  # → {}
```

---

## Probe Script

```python
import sys
import os
import tempfile

project_root = os.path.abspath("/home/fancy/Projects_Vault/FM-Agent")
workspace = tempfile.mkdtemp(prefix="fm_agent_probe_")
os.chdir(workspace)

try:
    sys.path.insert(0, project_root)

    from src.languages.codegraph import CodeGraphExtractor
    from src.incremental_reasoner import _codegraph_functions_by_file

    class MockExtractor:
        def get_functions_by_file(self, lang_key, proj_dir=None):
            cg_langs = {
                "python":     ["python"],
                "go":         ["go"],
                "rust":       ["rust"],
                "c":          ["c"],
                "cpp":        ["cpp"],
                "java":       ["java"],
                "javascript": ["javascript", "jsx"],
                "typescript": ["typescript", "tsx"],
            }
            if lang_key not in cg_langs:
                return {}
            return {os.path.join(project_root, "dummy.py"): {"func": "def f(): pass"}}

    original_from_proj_dir = CodeGraphExtractor.from_proj_dir
    CodeGraphExtractor.from_proj_dir = classmethod(lambda cls, proj_dir: MockExtractor())

    actual = _codegraph_functions_by_file(project_root, ["nonexistent_lang_key"])
    expected = {}

    if isinstance(actual, dict) and actual == expected:
        print(f"NOT CONFIRMED — no exception; returned {actual!r} (expected {expected!r})")
    elif isinstance(actual, dict):
        print(f"CONFIRMED — returned {actual!r} (expected {expected!r})")
    else:
        print(f"NOT CONFIRMED — returned {actual!r} instead of dict")

    CodeGraphExtractor.from_proj_dir = original_from_proj_dir

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — no exception; returned {} (expected {})
```
