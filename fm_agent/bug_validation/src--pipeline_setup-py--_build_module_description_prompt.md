# Bug Report: _build_module_description_prompt

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/pipeline_setup-py/_build_module_description_prompt.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If phases_json cannot be opened or its content is not valid JSON,
    behaves as if phases were an empty list.
  - Returns None when none of the modules named in modified_modules
    has a non-empty source_files array in phases_json.
  - Otherwise, returns a string containing an agent prompt. The prompt
    enumerates every module in modified_modules that still owns at least
    one source file according to phases_json, each formatted as a
    bulleted line identifying the module by its current phase number
    and module name. The prompt includes explicit constraints that the
    agent must: edit only the "description" field of the listed modules
    in fm_agent/phases.json; not modify "source_files", "phase", "name",
    "depends_on_phases", or the phase structure; not touch any unlisted
    module; keep the JSON valid; and not modify any project source file.
  - This function has no side effects: it does not write to any file.

---

### Actual Behavior

The function returns either None or a string. It attempts to open and parse the JSON file at `phases_json`; if an OSError or ValueError occurs (e.g., file missing, invalid JSON), the file is treated as containing no phases. A mapping from (phase, module name) to list of source files is built from the file's 'phases' array. For each module in `modified_modules`, if the corresponding source file list is non-empty, the module is included in a list of changes. If this list is empty, the function returns None. Otherwise, it returns a prompt string beginning with 'Here is a list of modules in fm_agent/phases.json:\n\n', followed by lines of the form '  - phase {phase} module "{name}"' for each included module, followed by a fixed instruction text. The function has no side effects on its arguments or persistent state. Formal logic: Let D be the parsed JSON object if file read/parse succeeds, otherwise {'phases': []}. Define M = { (p.get('phase'), m.get('name', '')) : list(m.get('source_files', [])) for p in D.get('phases', []) for m in p.get('modules', []) }. Let C = { m  modified_modules | M.get((m['phase'], m['module']), []) != [] }. Then (C = )  result = None; (C  )  result = 'Here is a list of modules in fm_agent/phases.json:\n\n' + '\n'.join(f"  - phase {m['phase']} module \"{m['module']}\"" for m in sorted(C)) + '\n\nPlease update the "description" field of each module above so that it accurately describes the source files it now owns.\nRules:\n- Edit ONLY the "description" field of the listed modules in fm_agent/phases.json.\n- Do NOT change any "source_files", "phase", "name", "depends_on_phases", or the phase structure in any way.\n- Do NOT touch modules that are not in the list above.\n- Keep the JSON valid.\n- Do NOT modify any project source file; only edit fm_agent/phases.json.'

---

## Code Evidence

Line 17-18: source_files_by_key[(phase.get("phase"), module.get("name", ""))] = list(module.get("source_files", []))

---

## Trigger Condition

The specification requires that only modules with a non-empty source_files array be listed. The code converts the value of 'source_files' to a list unconditionally. If the JSON contains a non-array value like a string, list() turns it into a non-empty list of characters, incorrectly including the module in the prompt. This violates the spec's definition of a non-empty source_files array.

---

## How to trigger the bug

When `phases.json` contains a module whose `source_files` field is a string (not an array), `list("some_string")` produces a non-empty list of characters like `['s', 'o', 'm', 'e', ...]`. The truthiness check `if not source_files_by_key.get(...)` on line 531 then treats this as a non-empty source files list, and the module is incorrectly included in the prompt. Per the specification, only modules with a non-empty **array** of source files should be listed — a string value should be treated as empty.

### Inputs

| Parameter | Value |
|-----------|-------|
| `modified_modules` | `[{"phase": 1, "module": "buggy_module"}]` |
| `phases_json` (file content) | `{"phases": [{"phase": 1, "modules": [{"name": "buggy_module", "source_files": "not_an_array_but_a_string"}]}]}` |

### Expected (spec-correct) Output

`None` — `source_files` is a string, not a non-empty array, so the module should be skipped.

### Actual (buggy) Output

A prompt string beginning with `Here is a list of modules in fm_agent/phases.json:\n\n  - phase 1 module "buggy_module"\n\nPlease update the "description" field...` — the string was converted to a non-empty character list via `list()`, so the module was incorrectly included.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.pipeline_setup import _build_module_description_prompt
import json, tempfile, os

buggy_json = {
    "phases": [{
        "phase": 1,
        "modules": [{
            "name": "buggy_module",
            "source_files": "not_an_array_but_a_string"
        }]
    }]
}
tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
json.dump(buggy_json, tmp)
tmp.close()

result = _build_module_description_prompt(
    [{"phase": 1, "module": "buggy_module"}], tmp.name)
os.unlink(tmp.name)

# actual (buggy) output: a prompt string including "buggy_module"
# expected (correct) output: None
print(result)
```

---

## Probe Script

```python
import sys
import json
import os
import tempfile

try:
    from src.pipeline_setup import _build_module_description_prompt
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# The spec says: only modules with a non-empty source_files **array** should be
# listed.  The bug: list() on a non-array value (like a string) produces a
# non-empty list of characters, which passes the truthiness check and
# incorrectly includes the module in the prompt.

# Create a temporary phases.json with source_files as a STRING (not an array).
buggy_json = {
    "phases": [
        {
            "phase": 1,
            "name": "Test Phase",
            "modules": [
                {
                    "name": "buggy_module",
                    "source_files": "not_an_array_but_a_string",
                    "description": "test module with string source_files"
                }
            ]
        }
    ]
}

tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
json.dump(buggy_json, tmp)
tmp.close()

try:
    result = _build_module_description_prompt(
        [{"phase": 1, "module": "buggy_module"}],
        tmp.name
    )
except Exception as e:
    print(f'ERROR: {e}')
    os.unlink(tmp.name)
    sys.exit(1)

os.unlink(tmp.name)

# Spec-correct behavior: source_files is a string, not a non-empty array, so
# the module should be SKIPPED and the function should return None.
# Buggy behavior: list("not_an_array...") → ['n','o','t',...] (non-empty),
# so the module is included in the prompt.
expected = None
passed = result != expected

if passed:
    print(f'CONFIRMED — source_files was a string, but list() turned it into '
          f'a non-empty char list, incorrectly including the module.')
    print(f'  actual  : {result[:120]}...' if result else '  actual  : None')
else:
    print(f'NOT CONFIRMED — actual matched expected: {result}')
```

### Probe Output

```
CONFIRMED — source_files was a string, but list() turned it into a non-empty char list, incorrectly including the module.
  actual  : Here is a list of modules in fm_agent/phases.json:

  - phase 1 module "buggy_module"

Please update the "description" f...
```
