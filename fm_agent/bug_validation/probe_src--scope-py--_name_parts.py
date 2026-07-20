import sys
import os

# Ensure repo root is on sys.path so 'src' package is importable.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.scope import _name_parts
except Exception as e:
    print(f'ERROR: Failed to import _name_parts from src.scope: {e}')
    sys.exit(1)

# Trigger condition from the bug report: input "a_b_c"
# Spec claim: every consecutive pair of underscore-separated tokens must be included.
# For "a_b_c", the underscore-split tokens are ["a", "b", "c"].
# Expected (spec-correct): {"a_b_c", "a_b", "b_c"}
# Actual (buggy): {"a_b_c"} — all tokens have length 1, filtered out, no pairs generated.

test_inputs = [
    ("a_b_c", {"a_b_c", "a_b", "b_c"}),
    ("x_y_z_w", {"x_y_z_w", "x_y", "y_z", "z_w"}),
    ("n1_n2", {"n1_n2"}),  # len(n1)=2, len(n2)=2, single pair "n1_n2"
]

all_passed = True

for name, expected in test_inputs:
    try:
        actual = _name_parts(name)
    except Exception as e:
        print(f'ERROR: _name_parts("{name}") raised: {e}')
        sys.exit(1)

    missing = expected - actual
    extra = actual - expected

    if missing:
        all_passed = False
        print(f'BUG REPRODUCED for "{name}"')
        print(f'  missing from actual: {missing}')
        print(f'  extra in actual: {extra}')
    else:
        print(f'OK for "{name}"')

if all_passed:
    print('NOT CONFIRMED — all test cases produced the expected output')
else:
    print('CONFIRMED — bug reproduced: consecutive underscore-separated pairs are missing when individual tokens have length <= 1')
