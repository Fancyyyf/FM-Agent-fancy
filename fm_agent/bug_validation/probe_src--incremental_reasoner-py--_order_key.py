"""
Probe script for bug: src--incremental_reasoner-py--_order_key

The _order_key function (line 1622 of src/incremental_reasoner.py) is a local
closure inside _update_specs_for_intent. It accesses order_index via closure.

Bug: _order_key returns (order_index.get(fqn, len(order_index)), fqn).
For absent FQNs, position = len(order_index). If any present FQN has a value
>= len(order_index), the absent FQN sorts BEFORE that present FQN, violating
the spec that absent FQNs must sort AFTER all present FQNs.

In the actual code, order_index is always constructed as:
    order_index = {fqn: i for i, fqn in enumerate(topdown)}
producing consecutive values 0..n-1, so the bug cannot manifest in practice.
"""
import sys


def _order_key_buggy(fqn, order_index):
    """Exact replica of the buggy _order_key logic (line 1622-1623)."""
    return (order_index.get(fqn, len(order_index)), fqn)


def test_bug_logic():
    """Demonstrate the bug with sparse order_index."""
    order_index = {"alpha": 100, "beta": 200}
    absent_fqns = ["gamma", "delta", "epsilon"]

    sort_keys = []
    for fqn in order_index:
        sort_keys.append(_order_key_buggy(fqn, order_index))
    for fqn in absent_fqns:
        sort_keys.append(_order_key_buggy(fqn, order_index))

    sorted_keys = sorted(sort_keys)
    sorted_names = [name for _, name in sorted_keys]

    absent_positions = []
    present_positions = []
    for i, name in enumerate(sorted_names):
        if name in absent_fqns:
            absent_positions.append(i)
        else:
            present_positions.append(i)

    bug_triggered = bool(absent_positions and present_positions and min(absent_positions) < max(present_positions))
    return bug_triggered, order_index, sorted_names, absent_positions, present_positions


def test_safe_construction():
    """Demonstrate the actual code construction does NOT trigger the bug."""
    topdown = ["alpha", "beta", "gamma"]
    order_index = {fqn: i for i, fqn in enumerate(topdown)}
    absent_fqns = ["delta", "epsilon"]

    sort_keys = []
    for fqn in order_index:
        sort_keys.append(_order_key_buggy(fqn, order_index))
    for fqn in absent_fqns:
        sort_keys.append(_order_key_buggy(fqn, order_index))

    sorted_keys = sorted(sort_keys)
    sorted_names = [name for _, name in sorted_keys]

    absent_positions = []
    present_positions = []
    for i, name in enumerate(sorted_names):
        if name in absent_fqns:
            absent_positions.append(i)
        else:
            present_positions.append(i)

    bug_triggered = bool(absent_positions and present_positions and min(absent_positions) < max(present_positions))
    return bug_triggered, order_index, sorted_names


def main():
    triggered, idx, names, apos, ppos = test_bug_logic()
    print(f"Test 1 (sparse order_index = {idx}):")
    print(f"  Sorted order: {names}")
    if triggered:
        print(f"  CONFIRMED: absent FQNs at positions {apos} sort BEFORE present FQNs at {ppos}")
        print(f"  Violates spec: absent FQNs must sort AFTER all present FQNs.")
    else:
        print("  NOT CONFIRMED: absent FQNs sort correctly.")

    triggered2, idx2, names2 = test_safe_construction()
    print(f"\nTest 2 (consecutive order_index = {idx2}):")
    print(f"  Sorted order: {names2}")
    if triggered2:
        print("  CONFIRMED: bug manifested even with safe construction!")
    else:
        print("  Absent FQNs sort correctly after all present FQNs.")
        print("  Actual code behavior: bug is latent, NOT triggerable in practice.")

    print("\n---")
    print("The _order_key function has a LOGICAL BUG: absent keys get")
    print("len(order_index) as position, which can be smaller than present key values.")
    print("Cannot trigger through public API because order_index is always")
    print("constructed with consecutive 0..n-1 values via enumerate().")
    print("\nNOT CONFIRMED")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
