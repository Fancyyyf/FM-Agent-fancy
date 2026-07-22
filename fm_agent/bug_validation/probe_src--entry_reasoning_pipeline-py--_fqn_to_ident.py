"""Probe for _fqn_to_ident bug: empty string when source-file component is the last FQN component."""
import sys
import os

# Add the project root to sys.path so the 'src' package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.entry_reasoning_pipeline import _fqn_to_ident
except Exception as e:
    print(f"ERROR: Failed to import _fqn_to_ident: {e}")
    sys.exit(1)

# --- Test cases ---
# Test case 1: Normal - source-file is NOT the last component
#   src::storage-cpp::LocalStorage::Flush -> "LocalStorage::Flush"
actual_1 = _fqn_to_ident("src::storage-cpp::LocalStorage::Flush")
expected_1 = "LocalStorage::Flush"
assert actual_1 == expected_1, f"Test 1 failed: got {actual_1!r}, expected {expected_1!r}"

# Test case 2: Normal - source-file is NOT the last component
#   src::checkpoint-cpp::RunCheckpoint -> "RunCheckpoint"
actual_2 = _fqn_to_ident("src::checkpoint-cpp::RunCheckpoint")
expected_2 = "RunCheckpoint"
assert actual_2 == expected_2, f"Test 2 failed: got {actual_2!r}, expected {expected_2!r}"

# Test case 3: BUG - source-file IS the last component
#   src::storage-cpp -> should be non-empty per spec, but returns ""
actual_3 = _fqn_to_ident("src::storage-cpp")
expected_3 = "storage-cpp"  # spec-correct: at minimum non-empty; reasonable value
passed_3 = (actual_3 != expected_3)  # bug is confirmed if they differ

# Test case 4: BUG - single component that IS a source-file
#   storage-cpp -> should be non-empty, returns ""
actual_4 = _fqn_to_ident("storage-cpp")
expected_4 = "storage-cpp"  # spec-correct: non-empty
passed_4 = (actual_4 != expected_4)  # bug is confirmed if they differ

# Test case 5: No source-file component
#   MyClass::myMethod -> "myMethod" (fallback)
actual_5 = _fqn_to_ident("MyClass::myMethod")
expected_5 = "myMethod"
assert actual_5 == expected_5, f"Test 5 failed: got {actual_5!r}, expected {expected_5!r}"

# --- Verdict ---
bug_confirmed = passed_3 and passed_4

if bug_confirmed:
    print(f"CONFIRMED")
    print(f"  Test 3 (src::storage-cpp):        actual={actual_3!r} | expected={expected_3!r}")
    print(f"  Test 4 (storage-cpp):             actual={actual_4!r} | expected={expected_4!r}")
    print(f"  Tests 1,2,5 (no-bug cases):       all passed")
else:
    print(f"NOT CONFIRMED")
