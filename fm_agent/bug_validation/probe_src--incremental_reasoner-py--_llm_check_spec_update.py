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
