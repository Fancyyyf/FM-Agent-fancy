import sys, os

# Ensure repo root on sys.path for package imports
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_ip161ped/snapshot')

import src.file_utils as fu

proj_dir = '/tmp/fm_agent_wt_FM-Agent_ip161ped/snapshot'

# Trigger: submodules=['nonexistent']
# Spec claim: yields only files whose project-relative path begins with 'nonexistent/'.
# Since no such files exist, expected output is empty sequence [].
# Actual bug: os.walk raises FileNotFoundError on non-existent directory.

try:
    actual = list(fu._iter_project_source_files(proj_dir, submodules=['nonexistent']))
    expected = []
    # Bug reproduced if actual != expected (which shouldn't happen since it should crash)
    # But if no crash, check the output
    if actual != expected:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
except FileNotFoundError as e:
    print(f'CONFIRMED — actual: FileNotFoundError raised ({e}) | expected: empty sequence []')
except OSError as e:
    # OSError is the parent of FileNotFoundError; catching it too for safety
    print(f'CONFIRMED — actual: OSError raised ({e}) | expected: empty sequence []')
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    sys.exit(1)
