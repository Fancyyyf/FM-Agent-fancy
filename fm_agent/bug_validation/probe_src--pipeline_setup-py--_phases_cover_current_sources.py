"""Probe script for bug: src--pipeline_setup-py--_phases_cover_current_sources

Bug: `if submodules` on line 686 treats empty list as falsy, skipping submodule
check when submodules=[]. Per spec condition (d), when submodules is not None
(which [] is), every listed source file must be under a submodule directory.
An empty list means no such directory exists → must return False.
"""
import sys
import os
import json
import tempfile
import shutil

# Add the project root to Python path so we can import src modules
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot')

try:
    from src.pipeline_setup import _phases_cover_current_sources

    # Create a temporary project directory with source files
    tmpdir = tempfile.mkdtemp(prefix='probe_phases_cover_')

    # Create source files under src/
    src_dir = os.path.join(tmpdir, 'src')
    os.makedirs(src_dir)
    with open(os.path.join(src_dir, 'main.py'), 'w') as f:
        f.write('def main():\n    pass\n')
    with open(os.path.join(src_dir, 'helper.py'), 'w') as f:
        f.write('def helper():\n    return 42\n')

    # Create a phases.json that lists both source files
    phases_json = os.path.join(tmpdir, 'phases.json')
    phases_data = {
        "phases": [
            {
                "phase": 1,
                "name": "Core",
                "modules": [
                    {
                        "name": "core_module",
                        "source_files": ["src/main.py", "src/helper.py"]
                    }
                ],
                "depends_on_phases": []
            }
        ]
    }
    with open(phases_json, 'w') as f:
        json.dump(phases_data, f)

    # --- Test 0: submodules=None → should return True (conditions a-c,e pass) ---
    result_none = _phases_cover_current_sources(phases_json, tmpdir, submodules=None)

    # --- Test 1 (BUG TARGET): submodules=[] → spec says should return False ---
    # Per spec condition (d): "when submodules is not None, every listed source
    # file path falls under at least one of the specified submodule directories."
    # An empty list [] is not None, so condition (d) applies. But [] provides
    # no valid submodule directories, so no source file can satisfy the check.
    # Expected: False.
    # Actual (bug): The code uses 'if submodules' which is falsy for [], so
    # the submodule check is skipped entirely. When all other conditions pass,
    # the function returns True — violating the spec.
    result_empty = _phases_cover_current_sources(phases_json, tmpdir, submodules=[])

    # Cleanup
    shutil.rmtree(tmpdir)

    # Bug confirmation: spec says should be False, but code returns True
    expected = False
    actual = result_empty
    passed = actual != expected  # True → bug reproduced

except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
    sys.exit(1)

# Report
print(f'submodules=None result: {result_none!r} (expected: True, sanity check)')
print(f'submodules=[]  result: {actual!r} (expected: False per spec)')

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
