"""Probe for _git: FileNotFoundError not covered by spec."""
import os
import sys
import subprocess

# Add repo root to Python path (probe is at fm_agent/bug_validation/, 3 levels deep)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Save original PATH and remove git from it to trigger FileNotFoundError
original_path = os.environ.get('PATH', '')
os.environ['PATH'] = '/tmp/no-git-here'

try:
    from src.incremental_reasoner import _collect_changed_functions

    # Call the function that contains the nested _git helper.
    # With git absent from PATH, the first subprocess.run(["git", ...]) inside _git
    # will raise FileNotFoundError — which the spec does not allow
    # (spec only permits CalledProcessError for nonzero exit codes).
    _collect_changed_functions('/tmp/dummy_proj_dir', 'dummy_commit_1234abcd')

    # If we reach here, no exception was raised → bug NOT reproduced
    print('NOT CONFIRMED — _collect_changed_functions completed without raising FileNotFoundError')

except FileNotFoundError:
    # The spec only allows CalledProcessError for nonzero exit codes.
    # FileNotFoundError is NOT in the spec → bug CONFIRMED.
    print('CONFIRMED — FileNotFoundError raised when git not found on PATH (spec only allows CalledProcessError)')

except subprocess.CalledProcessError as e:
    print(f'NOT CONFIRMED — CalledProcessError raised (as spec requires): {e}')

except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')

finally:
    os.environ['PATH'] = original_path
