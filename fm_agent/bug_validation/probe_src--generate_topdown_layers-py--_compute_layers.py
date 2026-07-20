"""Probe script for _compute_layers bug: topological layer ordering is reversed.

The spec requires layer(callee) <= layer(caller), but the code produces
layer(caller) < layer(callee) because it uses callers_map (instead of
callees_map) in Kahn's algorithm.
"""
import sys
sys.path.insert(0, '.')

from src.generate_topdown_layers import _compute_layers

# Simple DAG: A calls B
#   A ──→ B
# Spec requires: callee B at layer 0, caller A at layer 1
# Code produces: caller A at layer 0, callee B at layer 1 (reversed)
phase_fqns = {"A", "B"}
callees_map = {"A": {"B"}}  # A calls B
callers_map = {"B": {"A"}}  # A calls B

try:
    layers = _compute_layers(phase_fqns, callees_map, callers_map)

    # Find where A and B ended up
    a_layer = b_layer = None
    for layer_info in layers:
        if "A" in layer_info["functions"]:
            a_layer = layer_info["layer"]
        if "B" in layer_info["functions"]:
            b_layer = layer_info["layer"]

    # Spec says callee (B) <= caller (A), but code gives caller (A) < callee (B)
    # Bug is confirmed if caller's layer < callee's layer (wrong order)
    spec_violation = a_layer is not None and b_layer is not None and a_layer < b_layer

    if spec_violation:
        print(f'CONFIRMED — caller A at layer {a_layer}, callee B at layer {b_layer} '
              f'(spec requires callee layer <= caller layer)')
    else:
        print(f'NOT CONFIRMED — A at layer {a_layer}, B at layer {b_layer} '
              f'(caller-callee ordering matches spec)')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
