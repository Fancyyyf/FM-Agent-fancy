# Bug Report: _persist_analysis

**Source file:** `src/languages/erlang.py` (lines 408–464)
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Creates or overwrites the file .codegraph/erlang_callgraph.json under the
    directory identified by the resolved absolute path of proj_dir
  - The output file contains a single JSON object with the following guaranteed
    keys: "schema_version" (integer, value 1), "status" (string, value
    "success"), "backend" (string, value "elp"), "server_info" (the contents
    of analysis.server_info), "elp_command" (a list of strings), and
    "project_fingerprint" (a string digest)
  - The JSON object contains a "functions" key whose value is a list of
    {"id": function_id, "file": relative_path} objects, one per function in
    analysis.functions, where relative_path is the file path relative to the
    resolved proj_dir using "/" separators
  - The JSON object contains an "edges" key whose value is a list of
    {"caller", "caller_module", "caller_file", "callee"} objects, one per
    callee in analysis.edges, where "caller_file" is the relative path of the
    file containing the caller function
  - The write to the output file is atomic: the file at the target path is
    replaced only after the full JSON document has been written to a temporary
    file; if the write is interrupted, the target file either retains its
    previous contents (or does not exist) with no partial data
  - Raises OSError when the output directory cannot be created or when the
    output file cannot be written or replaced

---

### Actual Behavior

After the function returns (normally or via exception), the following post-condition holds. Let R = os.path.abspath(proj_dir), O_dir = os.path.join(R, '.codegraph'), O_path = os.path.join(O_dir, 'erlang_callgraph.json'). Let D be the dictionary {'schema_version': 1, 'status': 'success', 'backend': 'elp', 'server_info': analysis.server_info, 'elp_command': list(_elp_argv()), 'project_fingerprint': _fingerprint_digest(fingerprint), 'functions': a list of {'id': function_id, 'file': rel_path} for each (path, file_functions) in sorted(analysis.functions.items()) and each (function_id, _source) in file_functions with rel_path = os.path.relpath(path, R).replace(os.sep, '/'), 'edges': a list of {'caller': caller, 'caller_module': caller_module, 'caller_file': caller_files.get((caller, caller_module)), 'callee': callee} for each ((caller, caller_module), callees) in sorted(analysis.edges.items()) and each callee in sorted(callees)}. On normal return (no exception), O_dir exists and O_path is a regular file containing exactly json.dumps(D, indent=2, ensure_ascii=False)+'\\n', and no temporary file (created with prefix '.erlang_callgraph.' in O_dir) remains. On an exception before the atomic os.replace, O_path is in its pre-call state (existing with its old content or absent), and any temporary file is unlinked (best effort; OSError ignored). On an exception during or after a successful os.replace, the atomic semantics ensure O_path holds either the new content or the old content, and any temporary file is unlinked best effort. In all paths, the function does not modify other filesystem resources.

---

## Code Evidence

Line 13: caller_files[(function_id, caller_module)] = rel_path; Line 18: "caller_file": caller_files.get((caller, caller_module))

---

## Trigger Condition

When analysis.edges contains a caller that is not present in analysis.functions, caller_files does not contain an entry for the (caller, caller_module) key. The code falls back to None via .get(), producing "caller_file": null in the JSON output. This violates the specification which requires "caller_file" to be the relative path of the file containing the caller function.

---

## How to trigger the bug

The bug occurs when `analysis.edges` contains a caller function that is absent from `analysis.functions`. The `caller_files` dictionary (populated only by iterating `analysis.functions`) has no entry for that caller, so `caller_files.get((caller, caller_module))` returns `None`, producing `"caller_file": null` in the JSON output.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A temporary directory path |
| `fingerprint` | `("test", 1)` |
| `analysis.functions` | `{"/tmp/fake_src/callee.erl": [("callee_function", "some-source")]}` |
| `analysis.edges` | `{("orphan_caller", "orphan_module"): {"some_callee"}}` |
| `analysis.server_info` | `{"version": "1.0"}` |

### Expected (spec-correct) Output

```json
{
  "caller": "orphan_caller",
  "caller_module": "orphan_module",
  "caller_file": "relative/path/to/orphan_caller_file",
  "callee": "some_callee"
}
```

Where `caller_file` is the relative path of the file containing `orphan_caller`, not `null`.

### Actual (buggy) Output

```json
{
  "caller": "orphan_caller",
  "caller_module": "orphan_module",
  "caller_file": null,
  "callee": "some_callee"
}
```

`caller_file` is `null` because the `(caller, caller_module)` key is absent from `caller_files`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, sys, json, tempfile
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)
from src.languages.erlang import _persist_analysis, ErlangAnalysis

analysis = ErlangAnalysis(
    functions={"/tmp/fake_src/callee.erl": [("callee_function", "some-source")]},
    edges={("orphan_caller", "orphan_module"): {"some_callee"}},
    spans={},
    server_info={"version": "1.0"}
)

with tempfile.TemporaryDirectory() as proj_dir:
    _persist_analysis(proj_dir, ("test", 1), analysis)
    with open(os.path.join(proj_dir, ".codegraph", "erlang_callgraph.json")) as f:
        data = json.load(f)
    for edge in data["edges"]:
        if edge["caller"] == "orphan_caller":
            print(edge)
// actual (buggy) output: {'caller': 'orphan_caller', 'caller_module': 'orphan_module', 'caller_file': None, 'callee': 'some_callee'}
// expected (correct) output: {'caller': 'orphan_caller', 'caller_module': 'orphan_module', 'caller_file': '<relative path>', 'callee': 'some_callee'}
```

---

## Probe Script

```python
"""Probe for _persist_analysis bug: caller_file becomes null when edge caller is absent from functions."""
import os
import sys
import json
import tempfile

# The module is in src/languages/erlang.py
# We need to add the repo root to sys.path so the import resolves.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.languages.erlang import _persist_analysis, ErlangAnalysis
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Build an analysis where edges references a caller NOT in functions.
# functions: {"caller_function", "callee_function"} both present
# edges: caller "orphan_caller" → callee "some_callee" — orphan_caller NOT in functions
analysis = ErlangAnalysis(
    functions={
        "/tmp/fake_src/callee.erl": [("callee_function", "some-source")]
    },
    edges={
        ("orphan_caller", "orphan_module"): {"some_callee"}
    },
    spans={},
    server_info={"version": "1.0"}
)
fingerprint = ("test", 1)

with tempfile.TemporaryDirectory() as proj_dir:
    try:
        _persist_analysis(proj_dir, fingerprint, analysis)
    except Exception as e:
        print(f'ERROR calling _persist_analysis: {e}')
        sys.exit(1)

    output_path = os.path.join(proj_dir, ".codegraph", "erlang_callgraph.json")
    if not os.path.isfile(output_path):
        print(f'ERROR: output file not found at {output_path}')
        sys.exit(1)

    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    edges = data.get("edges", [])
    bug_found = False
    for edge in edges:
        if edge.get("caller") == "orphan_caller" and edge.get("caller_file") is None:
            bug_found = True
            break

    expected = "CONFIRMED"
    if bug_found:
        print(f'CONFIRMED — caller_file is null for edge with orphan caller. Edge: {json.dumps(edge)}')
    else:
        print(f'NOT CONFIRMED — caller_file was not null or edge not found. Edges: {json.dumps(edges)}')
```

### Probe Output

```
CONFIRMED — caller_file is null for edge with orphan caller. Edge: {"caller": "orphan_caller", "caller_module": "orphan_module", "caller_file": null, "callee": "some_callee"}
```
