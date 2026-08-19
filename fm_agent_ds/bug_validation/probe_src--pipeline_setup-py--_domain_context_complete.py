"""Probe script for bug: src--pipeline_setup-py--_domain_context_complete

Bug: _json_file_is_valid returns True for top-level JSON arrays, but
phases_data.get("phases", []) raises AttributeError since lists lack .get().
The function should return False per spec, not propagate an exception.
"""
import sys
import os
import tempfile
import shutil

# Ensure the repo root is on sys.path so 'import src' resolves.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.pipeline_setup import _domain_context_complete
except Exception as e:
    print(f'ERROR: Failed to import _domain_context_complete: {e}')
    sys.exit(1)

# Create an isolated temp directory for all fixtures and outputs.
tmp_dir = tempfile.mkdtemp(prefix="bug_probe_domain_context_")
try:
    # Step 1: Create phases.json with a top-level JSON array (valid JSON, not a dict).
    phases_path = os.path.join(tmp_dir, "phases.json")
    with open(phases_path, "w") as f:
        f.write('[{"phase": 1}]\n')

    # Step 2: Create engine_overview.txt so the existence check passes.
    domain_dir = os.path.join(tmp_dir, "spec_prompts", "domain_context")
    os.makedirs(domain_dir, exist_ok=True)
    overview_path = os.path.join(domain_dir, "engine_overview.txt")
    with open(overview_path, "w") as f:
        f.write("Engine overview placeholder\n")

    # Step 3: Call the function. Per spec it should return False, but the bug
    # causes an uncaught AttributeError because phases_data.get() fails on a list.
    actual = None
    exception_raised = False
    try:
        actual = _domain_context_complete(tmp_dir)
    except AttributeError as e:
        exception_raised = True
        print(f"DEBUG: Caught expected AttributeError: {e}", file=sys.stderr)
    except Exception as e:
        print(f'ERROR: Unexpected exception: {type(e).__name__}: {e}')
        sys.exit(1)

    # Step 4: Determine result.
    expected = False  # spec says it should return False

    if exception_raised:
        # Bug confirmed: function propagated an exception instead of returning False.
        print(f'CONFIRMED — actual: AttributeError raised | expected: return False')
    elif actual == expected:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
    else:
        print(f'NOT CONFIRMED — actual: {actual!r} | expected: {expected!r}') 

finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)
