import sys
import os
import tempfile

# Add repo root to Python path for import
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.generate_topdown_layers import _load_phases

    # Create a temp directory with a phases.json containing a JSON array (not dict)
    with tempfile.TemporaryDirectory() as tmpdir:
        phases_path = os.path.join(tmpdir, "phases.json")
        with open(phases_path, "w") as f:
            f.write('[1, 2, 3]')

        result = _load_phases(tmpdir)

        # The spec claims: "_load_phases returns a Python dict"
        # The actual code returns json.load() result — a list for array input
        # Bug confirmed if result is NOT a dict
        if not isinstance(result, dict):
            print(f'CONFIRMED — actual: {type(result).__name__} {result!r} | spec requires: dict')
        else:
            print(f'NOT CONFIRMED — actual matched expected: {type(result).__name__} {result!r}')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
