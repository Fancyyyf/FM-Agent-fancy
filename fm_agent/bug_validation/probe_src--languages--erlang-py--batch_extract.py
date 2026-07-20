"""Probe: Does batch_extract / _function_id produce non-unique function identifiers?

The spec requires each function_identifier to be unique within its source module.
The bug claim: functions with the same name but different arity produce duplicate IDs.
"""

import sys
import os
import tempfile

# Load the package via its entry point — repo root is two levels up from this script
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)
from src.languages.erlang import batch_extract, _function_id, _escape_component, _module_from_uri

def test_batch_extract_smoke():
    """Attempt batch_extract on a temp dir with Erlang files. Without ELP, returns {}."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a minimal .erl file
        erl_path = os.path.join(tmpdir, "test.erl")
        with open(erl_path, "w") as f:
            f.write("-module(test).\n-export([foo/1, foo/2]).\n\nfoo(1) -> one;\nfoo(2) -> two.\n")
        result = batch_extract(tmpdir)
        # Without ELP, spec says return empty dict — this is correct
        return isinstance(result, dict)

def test_same_name_different_arity():
    """Test: do functions with the same name but different arity get different IDs?

    The bug claims they produce duplicates. Arity IS in the ID, so they should differ.
    """
    uri = "file:///home/user/proj/mymodule.erl"
    fid1 = _function_id(uri, "foo/1")
    fid2 = _function_id(uri, "foo/2")
    fid3 = _function_id(uri, "bar/3")

    # All three should be different
    ids = [fid1, fid2, fid3]
    unique = len(set(ids))
    duplicates_exist = unique != len(ids)

    return {
        "ids": ids,
        "unique": unique == len(ids),
        "duplicates_exist": duplicates_exist,
    }

def test_escape_component_collisions():
    """Test: can _escape_component produce collisions between different function names?

    _escape_component escapes non-alphanumeric/non-underscore chars to _{hex}.
    Example: '-' (0x2D) → '_2d'. But '2d' is alphanumeric, so 'foo-bar' → 'foo_2dbar'.
    A function named 'foo_2dbar' would also become 'foo_2dbar'. This creates a collision.
    """
    esc1 = _escape_component("foo-bar")
    esc2 = _escape_component("foo_2dbar")
    esc3 = _escape_component("hello_world")
    esc4 = _escape_component("hello-world")
    # Additional collision: '@' (0x40) → '_40'
    esc5 = _escape_component("my@func")
    esc6 = _escape_component("my_40func")

    collisions = []
    if esc1 == esc2:
        collisions.append(f"'foo-bar' and 'foo_2dbar' both → '{esc1}'")
    if esc4 == esc3:
        collisions.append(f"'hello-world' and 'hello_world' both → '{esc3}'")
    if esc5 == esc6:
        collisions.append(f"'my@func' and 'my_40func' both → '{esc5}'")

    # For a full function_id collision, we also need same module + same arity.
    # Both my@func/1 and my_40func/1 are valid unquoted Erlang atoms.
    # _escape_component maps both to 'my_40func', so function_ids will be identical.
    uri = "file:///home/user/proj/mymodule.erl"

    # Test pair 1: quoted name with hyphen vs escaped literal
    fid_a = _function_id(uri, "'foo-bar'/1")
    fid_b = _function_id(uri, "foo_2dbar/1")
    collision_1 = fid_a == fid_b

    # Test pair 2: unquoted @ vs escaped literal (more practical collision)
    fid_c = _function_id(uri, "my@func/1")
    fid_d = _function_id(uri, "my_40func/1")
    collision_2 = fid_c == fid_d

    # Test pair 3: _escape_component already proves these collide
    # my@func → my_40func, my_40func → my_40func
    # With same module + same arity → full function_id collision

    fid_collision = collision_1 or collision_2

    return {
        "escape_collisions": collisions,
        "function_id_collision": fid_collision,
        "collision_1": {"a": fid_a, "b": fid_b, "collision": collision_1},
        "collision_2": {"c": fid_c, "d": fid_d, "collision": collision_2},
    }

def test_seen_dedup_scenario():
    """Test: what if the 'seen' set drops a legitimate function due to _function_id collision?

    In _analyze_project_uncached, each file has a 'seen' set that prevents duplicate
    function_ids from being added. If two different Erlang functions produce the same
    function_id (via _escape_component collision), the second one would be silently
    dropped. This is the actual bug.
    """
    uri = "file:///home/user/proj/mymodule.erl"
    # Simulate what ELP would return for two different Erlang functions
    # that happen to produce the same function_id via _escape_component.
    # Both my@func/1 and my_40func/1 are valid unquoted Erlang atoms
    # and both escape to the same string.
    labels = [
        ("my@func/1", "my_at_func() -> ok."),
        ("my_40func/1", "my_40func(X) -> X + 1."),
    ]
    seen = set()
    results = []
    for label, body in labels:
        try:
            fid = _function_id(uri, label)
        except ValueError:
            continue
        if fid in seen:
            results.append(("DROPPED", fid, label, body))
        else:
            seen.add(fid)
            results.append(("KEPT", fid, label, body))

    # Count: if both KEPT, no bug. If one DROPPED, bug confirmed.
    kept_count = sum(1 for r in results if r[0] == "KEPT")
    dropped_count = sum(1 for r in results if r[0] == "DROPPED")

    return {
        "results": results,
        "kept": kept_count,
        "dropped": dropped_count,
        "bug_confirmed": dropped_count > 0,
    }


def main():
    verdicts = []

    # Test 1: batch_extract smoke test
    try:
        smoke_ok = test_batch_extract_smoke()
        verdicts.append(("batch_extract_smoke", smoke_ok, None))
    except Exception as e:
        verdicts.append(("batch_extract_smoke", False, str(e)))

    # Test 2: same name, different arity → different IDs?
    try:
        result = test_same_name_different_arity()
        verdicts.append(("same_name_diff_arity", result["unique"], result))
    except Exception as e:
        verdicts.append(("same_name_diff_arity", False, str(e)))

    # Test 3: _escape_component collisions → function_id collisions?
    try:
        result = test_escape_component_collisions()
        verdicts.append(("escape_collision", not result["function_id_collision"], result))
    except Exception as e:
        verdicts.append(("escape_collision", False, str(e)))

    # Test 4: seen dedup scenario — actual bug reproduction
    try:
        result = test_seen_dedup_scenario()
        verdicts.append(("seen_dedup", not result["bug_confirmed"], result))
    except Exception as e:
        verdicts.append(("seen_dedup", False, str(e)))

    # Determine overall verdict
    bug_confirmed = any(
        category == "seen_dedup" and details.get("bug_confirmed", False)
        for category, _, details in verdicts
        if isinstance(details, dict)
    )

    if bug_confirmed:
        print("CONFIRMED — _function_id via _escape_component produces duplicate identifiers; seen set silently drops functions")
    else:
        print("NOT CONFIRMED — function identifiers include arity, same-name-different-arity produces unique IDs; no duplicates observed")

    # Print detailed results
    for category, passed, details in verdicts:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {category}: {details}")

    return 0 if not bug_confirmed else 1

if __name__ == "__main__":
    sys.exit(main())
