# Bug Report: _llm_check_spec_update

**Source file:** `/tmp/fm_agent_wt_FM-Agent__ro_f_c_/snapshot/fm_agent/extracted_functions/src/incremental_reasoner-py/_llm_check_spec_update.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Constructs an LLM prompt that presents: the developer intent, the
    function's current source code, its existing [SPEC] block (or an
    indication that none exists), its current [INFO] block with callee
    relationship hints (or an indication that none exists), and the list of
    known callee names
  - The prompt asks the LLM to decide whether the [SPEC] block must be updated
    to correctly describe the function's behavior after the intended
    modification, and if so, whether the [INFO] block must also be updated to
    reflect the new spec and any changes to the callee set
  - Sends the prompt to an LLM and validates the response against a JSON
    schema requiring keys: "spec_updated" (bool), "new_spec" (string),
    "info_updated" (bool), "new_info" (string), "updated_callees" (list of
    strings)
  - When the LLM returns valid, parseable JSON, spec_updated is True if and
    only if the [SPEC] block requires modification to remain a correct
    behavioral specification after the intended change; when True, new_spec
    contains the complete replacement [SPEC] block (markers included); when
    False, new_spec is the empty string
  - info_updated is True if and only if the [INFO] block was modified as a
    consequence of the spec update or a change in the callee set, including
    any of: adding entries for new callees, dropping entries for callees no
    longer called, or revising entries whose expected spec contradicts the new
    [SPEC]; when True, new_info contains the complete replacement [INFO] block
    (markers included); when False, new_info is the empty string
  - updated_callees is a list of callee name strings whose expected spec entry
    was added or changed in the new [INFO] block; the list is empty when no
    callee entries were affected or when info_updated is False
  - Returns None when the LLM produces no response, or when the response
    cannot be parsed as valid JSON matching the required schema
  - Domain knowledge files from under work_dir, if any exist at the expected
    location, are included in the prompt as additional context

---

### Actual Behavior

The function returns either a dict or None. Normal return: If the call to _llm_select_json succeeds (i.e., produces a valid JSON object that passes the schema validation specified internally by this function), then the return value is a dict with the following keys exactly: 'spec_updated' (a boolean), 'new_spec' (a string, possibly empty), 'info_updated' (a boolean), 'new_info' (a string, possibly empty), and 'updated_callees' (a list of strings). The values reflect the LLM's decision on whether the function's [SPEC] and/or [INFO] blocks need to be updated according to the developer_intent, given the current source, spec_block, info_block, callee_names, and any domain knowledge found under work_dir. Failure case: If _llm_select_json returns None (due to LLM call failure, no response, or invalid/non-conforming JSON), then the function returns None. No exceptions are raised; all error conditions are captured by the None return. The function has no side effects on the file system or on any of the mutable input arguments (proj_dir, work_dir, callee_names, etc.), except for the LLM tracing/logging performed internally by _llm_select_json (which may write trace events using the provided idx and stage identifier). Formal post-condition: Let r be the return value of _llm_check_spec_update(...). Then (r is dict)  (_llm_select_json returned a valid dict d that satisfies the schema validator, and r = d). (r is None)  (_llm_select_json returned None). If r is a dict, then r.keys() = {'spec_updated', 'new_spec', 'info_updated', 'new_info', 'updated_callees'} and typeof(r['spec_updated']) = bool, typeof(r['info_updated']) = bool, typeof(r['new_spec']) = str, typeof(r['new_info']) = str, typeof(r['updated_callees']) = list and  item  r['updated_callees'] : item is str.

---

## Code Evidence

Line 31: knowledge_section = _domain_knowledge_prompt_section(work_dir) (computed but never used); Line 32-40: prompt_content = ( ... ) (constructed without knowledge_section)

---

## Trigger Condition

The specification requires that domain knowledge files from under work_dir are included in the LLM prompt. The code computes knowledge_section but never inserts it into prompt_content, so the prompt sent to the LLM will lack this required context.

---

## How to trigger the bug

Despite the trigger condition claiming `knowledge_section` is "never inserted into prompt_content," the actual source code on line 130 contains `f"{knowledge_section}"` inside the parenthesized `prompt_content = (...)` expression. Python's implicit string concatenation within parentheses ensures that the interpolated value is joined with the adjacent string literal `"## Current function source\n\n"`. Therefore, the knowledge section **is** present in the LLM prompt, and the claimed bug does not exist.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `/tmp/test_proj` |
| work_dir | `/tmp/test_work` |
| idx | `0` |
| fqn | `test::func` |
| lang_key | `python` |
| comment_prefix | `#` |
| developer_intent | `Add logging` |
| spec_block | `# [SPEC]\n# test spec\n# [SPEC]` |
| info_block | `None` |
| callee_names | `['helper']` |
| source | `def func():\n    pass\n` |

### Expected (spec-correct) Output

The `prompt_content` passed to `_llm_select_json` should contain the domain knowledge text.

### Actual (buggy) Output

The `prompt_content` passed to `_llm_select_json` **does** contain the domain knowledge text (`TEST_DOMAIN_KNOWLEDGE_MARKER_v4x9` was found in the captured prompt). The code at line 130 (`f"{knowledge_section}"`) correctly interpolates the knowledge section.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
import os

# Mock _domain_knowledge_prompt_section to return a known marker
# Mock _llm_select_json to capture prompt_content
# Import _llm_check_spec_update from the extracted functions module
# Call the function with test inputs

# actual (buggy) output: knowledge_section IS present in prompt_content
# expected (correct) output: knowledge_section should be present in prompt_content
```

---

## Probe Script

```python
import sys
import os
import json
import importlib.util

# ---------------------------------------------------------------------------
# 1. Load the function module dynamically with mocked dependencies
# ---------------------------------------------------------------------------

extracted_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..',
    'extracted_functions', 'src', 'incremental_reasoner-py'
)

# Mock modules the function depends on so we don't need real LLM / fs access
class MockModule:
    pass

# _domain_knowledge_prompt_section mock — returns a distinctive canned string
TEST_KNOWLEDGE_STRING = "TEST_DOMAIN_KNOWLEDGE_MARKER_v4x9"

def _domain_knowledge_prompt_section(work_dir):
    return f"## User-provided domain knowledge\n\n{TEST_KNOWLEDGE_STRING}\n\n"

# _llm_select_json mock — captures prompt_content, returns a valid dict
captured_prompts = []
def _llm_select_json(work_dir, prompt_content, stage, validator,
                     schema_description, trace_meta=None):
    captured_prompts.append(prompt_content)
    return {
        "spec_updated": False,
        "new_spec": "",
        "info_updated": False,
        "new_info": "",
        "updated_callees": []
    }

# _validate_spec_update mock — just returns the input dict
def _validate_spec_update(data):
    return data

# _llm_provider_client, LLM_MODEL, logging mocks
_llm_provider_client = object()
LLM_MODEL = "mock-model"

class FakeLogging:
    @staticmethod
    def error(*args, **kwargs):
        pass
logging = FakeLogging()

# load_staged_domain_knowledge_text — already unused in the mocked path but define anyway
def load_staged_domain_knowledge_text(work_dir):
    return TEST_KNOWLEDGE_STRING

# Set up the mock modules in sys.modules so the import picks them up
for name, obj in [
    ("_domain_knowledge_prompt_section", _domain_knowledge_prompt_section),
    ("_llm_select_json", _llm_select_json),
    ("_validate_spec_update", _validate_spec_update),
]:
    mod = MockModule()
    mod.__name__ = name
    setattr(sys.modules.setdefault(name, mod), name.split('.')[-1], obj)
    sys.modules[name] = mod

# ---------------------------------------------------------------------------
# 2. Import _llm_check_spec_update from the extracted-functions file
# ---------------------------------------------------------------------------
mod_path = os.path.join(extracted_dir, '_llm_check_spec_update.py')
spec = importlib.util.spec_from_file_location('_llm_check_spec_update', mod_path)

# Crucial: set up sys.modules BEFORE loading so the internal imports resolve
# The file does "from _domain_knowledge_prompt_section import ...", etc.
# We need those names available in the module's namespace.

# Simpler approach: exec the file with a custom globals dict
globals_for_func = {
    '__name__': '_llm_check_spec_update',
    '__file__': mod_path,
    '_domain_knowledge_prompt_section': _domain_knowledge_prompt_section,
    '_llm_select_json': _llm_select_json,
    '_validate_spec_update': _validate_spec_update,
    '_llm_provider_client': _llm_provider_client,
    'LLM_MODEL': LLM_MODEL,
    'logging': logging,
    'os': os,
}

with open(mod_path, 'r') as f:
    source = f.read()
# Strip the SPEC/INFO comment blocks at the top (lines starting with #)
lines = source.split('\n')
code_lines = []
in_spec_info = True
for line in lines:
    stripped = line.strip()
    if in_spec_info and (stripped.startswith('#') or stripped == ''):
        # Check if we've passed the INFO block - look for "def " pattern
        if stripped.startswith('def '):
            in_spec_info = False
            code_lines.append(line)
        elif stripped.startswith('# [SPLIT]'):
            # This marks the boundary between INFO and code
            code_lines.append('')  # just a blank
        elif stripped.startswith('# [INFO]'):
            code_lines.append('')
        else:
            code_lines.append('')
    else:
        in_spec_info = False
        code_lines.append(line)

exec_code = '\n'.join(code_lines)

try:
    exec(exec_code, globals_for_func)
except Exception as e:
    print(f'ERROR: Failed to exec module: {e}')
    sys.exit(1)

_llm_check_spec_update = globals_for_func.get('_llm_check_spec_update')
if _llm_check_spec_update is None:
    print('ERROR: _llm_check_spec_update not found after exec')
    sys.exit(1)

# ---------------------------------------------------------------------------
# 3. Execute the test
# ---------------------------------------------------------------------------
captured_prompts.clear()

result = _llm_check_spec_update(
    proj_dir='/tmp/test_proj',
    work_dir='/tmp/test_work',
    idx=0,
    fqn='test::func',
    lang_key='python',
    comment_prefix='#',
    developer_intent='Add logging',
    spec_block='# [SPEC]\n# test spec\n# [SPEC]',
    info_block=None,
    callee_names=['helper'],
    source='def func():\n    pass\n',
)

# Check: was TEST_KNOWLEDGE_STRING included in the prompt?
if len(captured_prompts) == 0:
    print('ERROR: _llm_select_json was never called')
    sys.exit(1)

prompt = captured_prompts[0]
knowledge_in_prompt = TEST_KNOWLEDGE_STRING in prompt

# Check result shape
result_ok = (
    result is not None
    and isinstance(result, dict)
    and result.get('spec_updated') is False
    and result.get('new_spec') == ''
    and result.get('info_updated') is False
    and result.get('new_info') == ''
    and result.get('updated_callees') == []
)

if knowledge_in_prompt:
    print(f'NOT CONFIRMED — knowledge_section IS present in prompt_content; '
          f'TEST_KNOWLEDGE_STRING found in prompt. '
          f'The code at line 130 f"{{knowledge_section}}" does interpolate '
          f'knowledge_section into the LLM prompt. '
          f'Result valid: {result_ok}')
else:
    print(f'CONFIRMED — knowledge_section is MISSING from prompt_content; '
          f'TEST_KNOWLEDGE_STRING NOT found in prompt. '
          f'Result valid: {result_ok}')
```

### Probe Output

```
NOT CONFIRMED — knowledge_section IS present in prompt_content; TEST_KNOWLEDGE_STRING found in prompt. The code at line 130 f"{knowledge_section}" does interpolate knowledge_section into the LLM prompt. Result valid: True
```
