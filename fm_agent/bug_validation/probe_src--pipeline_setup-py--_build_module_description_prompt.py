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
