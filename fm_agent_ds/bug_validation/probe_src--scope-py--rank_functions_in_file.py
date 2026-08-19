"""Probe script for bug src--scope-py--rank_functions_in_file.

Tests whether rank_functions_in_file returns a properly structured list of dicts
with keys (file, name, lineno, end_lineno, score, reason), or falls off the end
returning None.
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path so the package entry point resolves
project_root = os.path.dirname(os.path.abspath(__file__))
# The project root is the workspace root
repo_root = os.environ.get("FM_AGENT_REPO_ROOT", os.getcwd())

# We need the repo root in sys.path so that config, src package resolve
for p in [repo_root, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from src.scope import rank_functions_in_file

    # Create a temp test fixtures directory
    fixtures_dir = Path("/tmp/opencode/bug_validation_fixtures")
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    test_file = fixtures_dir / "test_module.py"

    # Parse signals matching the expected structure
    signals: dict[str, set[str]] = {
        'traceback_funcs': set(),
        'backtick_idents': {'process_data', 'validate_input', 'format_output'},
        'dotted_refs':     set(),
        'dotted_classes':  set(),
        'plain_idents':    set(),
        'exception_types': set(),
        'all_words':       {'process', 'data', 'validate', 'input', 'format', 'output'},
    }

    result = rank_functions_in_file(
        filepath=str(test_file),
        src_path=test_file,
        issue="Need to process data validation and output formatting",
        signals=signals,
        top_k=2,
    )

    # Verify the spec claims
    spec_required_keys = {'file', 'name', 'lineno', 'end_lineno', 'score', 'reason'}

    if result is None:
        print("CONFIRMED — rank_functions_in_file returned None (spec requires list of dicts)")
    elif not isinstance(result, list):
        print(f"CONFIRMED — rank_functions_in_file returned {type(result).__name__} instead of list")
    elif len(result) > 2:
        print(f"CONFIRMED — result length {len(result)} > top_k=2 (spec requires length ≤ top_k)")
    else:
        # Check each entry has all required keys
        missing_keys = False
        wrong_types = False
        for i, entry in enumerate(result):
            if not isinstance(entry, dict):
                wrong_types = True
                print(f"CONFIRMED — entry[{i}] is not a dict")
                break
            for key in spec_required_keys:
                if key not in entry:
                    missing_keys = True
                    print(f"CONFIRMED — entry[{i}] missing key '{key}'")
                    break
            if missing_keys or wrong_types:
                break

        if not missing_keys and not wrong_types:
            # Verify scores are sorted descending
            scores = [e['score'] for e in result]
            is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
            if not is_sorted:
                print(f"CONFIRMED — scores not sorted descending: {scores}")
            else:
                print(
                    f"NOT CONFIRMED — rank_functions_in_file returned valid list of "
                    f"{len(result)} dict(s) with correct keys, scores sorted descending. "
                    f"The function correctly returns result (line 798 of src/scope.py)."
                )
                sys.exit(0)

except ImportError as e:
    print(f"ERROR: Could not import src.scope: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
