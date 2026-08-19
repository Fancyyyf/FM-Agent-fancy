import sys
import os

# The probe is run from the repo root. Ensure src/ is importable.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_project_root, 'src'))

try:
    from configure_llm import update_llm_settings_toml_text
except Exception as e:
    print(f'ERROR importing module: {e}')
    sys.exit(1)

# Test: input TOML with quoted key "name" under [llm]
# The spec says the old value should be replaced with the new one.
# The bug: _KV_RE regex only matches bare keys [A-Za-z0-9_]+,
# so quoted keys like "name" are not recognized. The old line
# is preserved AND a new bare-key line is appended — producing duplicates.
text = '[llm]\n"name" = "old-model"\nprovider = "old-provider"\n'
updates = {"name": "new-model"}

try:
    actual = update_llm_settings_toml_text(text, updates)
except Exception as e:
    print(f'ERROR calling function: {e}')
    sys.exit(1)

# Check for the bug: duplicate "name" entries
# Old quoted "name" line should remain + new "name" line should be appended
has_quoted_name = '"name"' in actual
has_bare_name_assignment = 'name ' in actual or 'name=' in actual or '\nname' in actual

# Count how many lines set "name" (either quoted or bare)
import re
name_lines = [l for l in actual.split('\n') if l.strip() and 'name' in l and '=' in l]
duplicate_keys = len(name_lines) > 1

if duplicate_keys:
    print(f'CONFIRMED — duplicate "name" keys found in output ({len(name_lines)} occurrences)')
    print(f'  Actual output: {actual!r}')
    print(f'  Expected: single "name" key with value "new-model"')
else:
    print(f'NOT CONFIRMED — no duplicate keys found: {actual!r}')
