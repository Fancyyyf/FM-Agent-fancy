"""Probe for bug ID: src--call_graph_edges-py--_parse_callee

Trigger condition: When value is a dict with info_names as an integer (e.g., 123),
the code should NOT silently return a CalleeTarget (treating it as empty tuple).
The spec requires that invalid info_names should be rejected (raise an error).
"""

import os
import sys
import tempfile
import json

# Ensure workspace root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

from src.call_graph_edges import load_call_edges


def test_int_info_names():
    """
    Test: callee.info_names is an integer (123).
    Expected (spec-correct): raise an error because 123 cannot yield a tuple of string names.
    Buggy claim: code silently treats it as empty tuple and returns CalleeTarget.
    """
    edge_json = {
        "edges": [
            {
                "caller": {"fqn": "test::func", "callsite_names": ["test_call"]},
                "callee": {"fqn": "target::func", "info_names": 123},
            }
        ]
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(edge_json, f)
        tmp_path = f.name

    try:
        edges = load_call_edges(tmp_path)
        # If we get here, no error was raised — the bug claim might be confirmed
        if len(edges) > 0:
            info_names = edges[0].callee.info_names
            print(
                f"CONFIRMED — silently returned CalleeTarget with info_names={info_names!r}"
            )
        else:
            print(
                "CONFIRMED — silently returned empty result (treated as empty tuple)"
            )
    except ValueError as e:
        # ValueError raised — correct behavior per spec
        print(f"NOT CONFIRMED — actual matched expected: ValueError raised: {e}")
    except Exception as e:
        print(f"NOT CONFIRMED — unexpected exception type: {type(e).__name__}: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def test_list_with_int_item():
    """
    Test: callee.info_names is a list containing an integer ["foo", 123].
    Expected (spec-correct): raise an error because 123 is not a string.
    Buggy claim: code might silently skip non-string items.
    """
    edge_json = {
        "edges": [
            {
                "caller": {"fqn": "test::func", "callsite_names": ["test_call"]},
                "callee": {"fqn": "target::func", "info_names": ["foo", 123]},
            }
        ]
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(edge_json, f)
        tmp_path = f.name

    try:
        edges = load_call_edges(tmp_path)
        if len(edges) > 0:
            info_names = edges[0].callee.info_names
            print(
                f"CONFIRMED — silently returned CalleeTarget with info_names={info_names!r}"
            )
        else:
            print("CONFIRMED — silently returned empty result")
    except ValueError as e:
        print(f"NOT CONFIRMED — actual matched expected: ValueError raised: {e}")
    except Exception as e:
        print(f"NOT CONFIRMED — unexpected exception type: {type(e).__name__}: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def test_dict_info_names():
    """
    Test: callee.info_names is a dict like {"a": 1}.
    Expected (spec-correct): raise an error because dict is not a list of strings.
    Buggy claim: code might silently treat it as empty tuple.
    """
    edge_json = {
        "edges": [
            {
                "caller": {"fqn": "test::func", "callsite_names": ["test_call"]},
                "callee": {"fqn": "target::func", "info_names": {"a": 1}},
            }
        ]
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(edge_json, f)
        tmp_path = f.name

    try:
        edges = load_call_edges(tmp_path)
        if len(edges) > 0:
            info_names = edges[0].callee.info_names
            print(
                f"CONFIRMED — silently returned CalleeTarget with info_names={info_names!r}"
            )
        else:
            print("CONFIRMED — silently returned empty result")
    except ValueError as e:
        print(f"NOT CONFIRMED — actual matched expected: ValueError raised: {e}")
    except Exception as e:
        print(f"NOT CONFIRMED — unexpected exception type: {type(e).__name__}: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


if __name__ == "__main__":
    test_int_info_names()
    test_list_with_int_item()
    test_dict_info_names()
