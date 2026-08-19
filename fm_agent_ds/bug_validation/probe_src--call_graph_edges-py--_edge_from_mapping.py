"""Probe for _edge_from_mapping bug: test whether malformed caller/callee
sub-objects raise errors with source path included, as the spec requires."""

import json
import sys
import tempfile
import os
from pathlib import Path

# This is the "public entry point" for the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.call_graph_edges import load_call_edges


def make_temp_json(data, tmpdir):
    """Create a temp JSON file with the given data."""
    path = os.path.join(tmpdir, "test_edges.json")
    with open(path, "w") as f:
        json.dump(data, f)
    return path


def run_test(label, edges, should_raise=True):
    """Run a single test case through load_call_edges."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = make_temp_json({"edges": edges}, tmpdir)
        try:
            result = load_call_edges(path)
            if should_raise:
                return False, f"{label}: expected error but got result {result}"
            return True, None
        except ValueError as e:
            if not should_raise:
                return False, f"{label}: unexpected error: {e}"
            msg = str(e)
            if path not in msg:
                return False, f"{label}: source path '{path}' not in error message: {msg}"
            return True, None
        except Exception as e:
            return False, f"{label}: unexpected exception type {type(e).__name__}: {e}"


def main():
    results = []
    source_file = "test_edges.json"

    # Test 1: caller is a string (not dict) — should raise with source
    ok, err = run_test(
        "caller-as-string",
        [{"caller": "not-a-dict", "callee": {"fqn": "some_func"}}],
    )
    if ok:
        results.append(("PASS", "caller-as-string: raised error with source path ✓"))
    else:
        results.append(("FAIL", err))

    # Test 2: callee is a string (not dict) — should raise with source
    ok, err = run_test(
        "callee-as-string",
        [{"caller": {"fqn": "some_func"}, "callee": "not-a-dict"}],
    )
    if ok:
        results.append(("PASS", "callee-as-string: raised error with source path ✓"))
    else:
        results.append(("FAIL", err))

    # Test 3: caller key missing entirely — should raise with source
    ok, err = run_test(
        "caller-missing-key",
        [{"callee": {"fqn": "some_func"}}],
    )
    if ok:
        results.append(("PASS", "caller-missing-key: raised error with source path ✓"))
    else:
        results.append(("FAIL", err))

    # Test 4: callee key missing entirely — should raise with source
    ok, err = run_test(
        "callee-missing-key",
        [{"caller": {"fqn": "some_func"}}],
    )
    if ok:
        results.append(("PASS", "callee-missing-key: raised error with source path ✓"))
    else:
        results.append(("FAIL", err))

    # Test 5: caller is a list (not dict) — should raise with source
    ok, err = run_test(
        "caller-as-list",
        [{"caller": [1, 2, 3], "callee": {"fqn": "some_func"}}],
    )
    if ok:
        results.append(("PASS", "caller-as-list: raised error with source path ✓"))
    else:
        results.append(("FAIL", err))

    # Test 6: callee is a list (not dict) — should raise with source
    ok, err = run_test(
        "callee-as-list",
        [{"caller": {"fqn": "some_func"}, "callee": [1, 2, 3]}],
    )
    if ok:
        results.append(("PASS", "callee-as-list: raised error with source path ✓"))
    else:
        results.append(("FAIL", err))

    # Print results
    all_passed = all(status == "PASS" for status, _msg in results)
    for status, msg in results:
        print(f"[{status}] {msg}")

    if all_passed:
        print("NOT CONFIRMED — all malformed sub-object cases raised ValueError with source path in message, matching the spec")
    else:
        print("CONFIRMED — at least one malformed sub-object case did not raise error with source path")


if __name__ == "__main__":
    main()
