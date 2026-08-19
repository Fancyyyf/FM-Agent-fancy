import sys
import os

# Ensure the repo root is on the path for the entry-point import
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.generate_topdown_layers import _compute_layers

    # Minimal test: A calls B
    # callees_map: A -> {B}   (A calls B)
    # callers_map: B -> {A}   (B is called by A)
    phase_fqns = ["A", "B"]
    callees_map = {"A": {"B"}}
    callers_map = {"B": {"A"}}

    actual = _compute_layers(phase_fqns, callees_map, callers_map)

    # Extract fqn -> layer assignments
    actual_assignments = {}
    for layer_info in actual:
        for fqn in layer_info["functions"]:
            actual_assignments[fqn] = layer_info["layer"]

    caller_layer = actual_assignments["A"]
    callee_layer = actual_assignments["B"]

    # Spec claim: callee's layer is STRICTLY LESS than caller's layer
    # i.e., for edge A -> B: B.layer < A.layer
    # Bug: code uses callers_map, so caller gets assigned first
    # Bug confirmed if callee.layer >= caller.layer
    bug_exists = callee_layer >= caller_layer

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if bug_exists:
    print(
        f"CONFIRMED — caller A at layer {caller_layer}, callee B at layer {callee_layer} "
        f"(callee_layer >= caller_layer, but spec requires callee_layer < caller_layer)"
    )
else:
    print(
        f"NOT CONFIRMED — callee B at layer {callee_layer}, caller A at layer {caller_layer} "
        f"(callee_layer < caller_layer as spec requires)"
    )
