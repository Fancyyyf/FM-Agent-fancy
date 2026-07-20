import os
import sys

# Script is at fm_agent/bug_validation/probe_...py; repo root is 2 levels up
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    from src.entry_reasoning_pipeline import _entry_func_source_rel
except ImportError as e:
    print(f'ERROR (import): {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Trigger condition: FQN with leading "::" produces empty first component.
# Claim: os.path.join yields absolute path (e.g. "/loader.cpp" on Unix),
# violating the spec that requires a relative path.

TEST_CASES = [
    # (entry_func, expected_relative_path, description)
    ("::loader-cpp::loadData", "loader.cpp",
     "Leading :: with two components after"),
    ("::src::loader-cpp::loadData", "src/loader.cpp",
     "Leading :: with three components after"),
    ("::module-py::loadData", "module.py",
     "Leading :: general case"),
]

confirmed = False
for entry_func, expected_rel, desc in TEST_CASES:
    try:
        actual = _entry_func_source_rel(entry_func)
        is_absolute = os.path.isabs(actual)
        is_correct = actual == expected_rel
        bug_reproduced = is_absolute or not is_correct

        if bug_reproduced:
            print(f'BUG [{desc}] (is_absolute={is_absolute}, is_correct={is_correct})')
            print(f'  entry_func  = {entry_func!r}')
            print(f'  actual      = {actual!r}')
            print(f'  expected    = {expected_rel!r}')
            confirmed = True
        else:
            print(f'OK [{desc}]: {entry_func!r} -> {actual!r} (relative, correct)')
    except Exception as e:
        print(f'ERROR [{desc}]: {e}')

if confirmed:
    print('CONFIRMED — buggy behavior detected')
else:
    print('NOT CONFIRMED — all test cases returned correct relative paths')
