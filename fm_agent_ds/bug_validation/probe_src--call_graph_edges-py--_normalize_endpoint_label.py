import sys
import os

# Ensure the repo root is on the import path (public entry-point rule)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from src.call_graph_edges import normalize_fqn_label

    # Input that triggers the bug: path with parent dir ".." prefix
    # lstrip("./") in _normalize_endpoint_label removes ALL leading '.' and '/'
    # characters, so "../foo.c::func" loses the ".." parent component.
    label = "../foo.c::func"

    actual = normalize_fqn_label(label)
    # Spec-correct: only leading "./" prefix stripped, so ".." parent is preserved
    expected = "..::foo-c::func"

    passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
