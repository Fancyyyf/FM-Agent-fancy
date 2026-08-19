"""Probe script for bug: src--incremental_reasoner-py--_opencode_generate_spec

The bug claim: A SyntaxError at line 33 of src/incremental_reasoner.py
prevents the module from compiling, so _opencode_generate_spec is never defined.
"""
import sys
import os

# Ensure the repo root is on sys.path for package imports
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

all_checks_passed = True

# Test 1: Can the module be compiled directly?
print("Check 1: Compiling src/incremental_reasoner.py...", end=" ")
try:
    import py_compile
    py_compile.compile(
        os.path.join(REPO_ROOT, 'src', 'incremental_reasoner.py'),
        doraise=True,
    )
    print("OK")
except SyntaxError as e:
    print(f"FAILED — SyntaxError: {e}")
    all_checks_passed = False

# Test 2: Can the module be imported?
print("Check 2: Importing src.incremental_reasoner...", end=" ")
try:
    import src.incremental_reasoner as mod  # noqa: F811
    print("OK")
except SyntaxError as e:
    print(f"FAILED — SyntaxError: {e}")
    all_checks_passed = False
except Exception as e:
    print(f"FAILED — {type(e).__name__}: {e}")
    all_checks_passed = False

# Test 3: Is _opencode_generate_spec defined and callable?
print("Check 3: _opencode_generate_spec defined and callable?...", end=" ")
try:
    from src.incremental_reasoner import _opencode_generate_spec
    if callable(_opencode_generate_spec):
        print("OK — callable function")
    else:
        print("FAILED — not callable")
        all_checks_passed = False
except Exception as e:
    print(f"FAILED — {type(e).__name__}: {e}")
    all_checks_passed = False

# Print verdict
# The spec-claim (buggy behavior): SyntaxError prevents compilation, function undefined
# The actual behavior: module compiles and imports cleanly, function is callable
if all_checks_passed:
    print('NOT CONFIRMED — Module compiles and imports successfully; '
          '_opencode_generate_spec is defined and callable. '
          'No SyntaxError at line 33 or anywhere else.')
else:
    print('CONFIRMED — Bug reproduced: module fails to compile or function is not callable.')
