"""Probe script for bug: src--incremental_reasoner-py--_update_specs_for_intent

Tests whether importing _update_specs_for_intent raises an IndentationError
as claimed by the logic verification result.
"""
import sys
import os
import importlib.util

# The probe runs from the repo root. The extracted function file is at:
# fm_agent/extracted_functions/src/incremental_reasoner-py/_update_specs_for_intent.py
# Probe is at: fm_agent/bug_validation/probe_...py
probe_dir = os.path.dirname(os.path.abspath(__file__))
# probe_dir is fm_agent/bug_validation; going up two levels reaches repo root
repo_root = os.path.dirname(os.path.dirname(probe_dir))
# Now repo_root/fm_agent/extracted_functions/... should work
extracted_path = os.path.join(
    repo_root, 'fm_agent', 'extracted_functions', 'src',
    'incremental_reasoner-py', '_update_specs_for_intent.py'
)

confirmed = None
error_msg = None
actual = None
expected = "IndentationError raised, function not created"

try:
    spec = importlib.util.spec_from_file_location(
        '_update_specs_for_intent_probe',
        extracted_path
    )
    mod = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(mod)
        fn = getattr(mod, '_update_specs_for_intent', None)
        if fn is not None and callable(fn):
            actual = (
                "Function _update_specs_for_intent exists and is callable "
                "(extracted file imported successfully, no IndentationError)"
            )
            confirmed = False
        else:
            actual = (
                "Module loaded but _update_specs_for_intent not found as callable"
            )
            confirmed = False
    except IndentationError as e:
        actual = f"IndentationError: {e}"
        confirmed = True
    except SyntaxError as e:
        actual = f"SyntaxError: {e}"
        confirmed = True

except Exception as e:
    error_msg = f'{type(e).__name__}: {e}'

if confirmed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
elif confirmed is False:
    print(f'NOT CONFIRMED — actual: {actual!r}')
else:
    print(f'ERROR: {error_msg}')
