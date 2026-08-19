import sys
import os
import tempfile

# Probe must be run from repo root; add repo root to sys.path for imports
sys.path.insert(0, os.getcwd())

# Create a fresh temp directory owned by the probe for any runtime artifacts
probe_workspace = tempfile.mkdtemp(prefix="fm_agent_probe_")

try:
    from src.languages.erlang import _symbol_range

    bug_triggered = False

    # Trigger condition: symbol['location'] is a truthy non-dict (e.g., a string)
    # Spec: should return None (location does not map to a truthy dict containing 'range')
    # Bug: (symbol.get("location") or {}).get("range") calls .get() on the string → AttributeError
    symbol = {"location": "L42C12-L42C24", "name": "some_func"}

    try:
        actual = _symbol_range(symbol)
        # No exception → bug not reproduced
        print(f'NOT CONFIRMED — no exception raised; actual: {actual!r} | expected: None')
    except AttributeError as e:
        bug_triggered = True
        print(f'CONFIRMED — AttributeError: {e} | expected: None (spec requires returning None)')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    import shutil
    shutil.rmtree(probe_workspace, ignore_errors=True)
