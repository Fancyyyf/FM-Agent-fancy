"""Probe script for bug: _load_json_edges doesn't wrap _edge_from_mapping exceptions.

Bug ID: src--call_graph_edges-py--_load_json_edges

Trigger condition: When an element of the 'edges' array is a dict not convertible to
a CallEdge (e.g., missing required keys), _edge_from_mapping may raise a non-ValueError
exception. The spec requires ValueError be raised.
"""
import json
import os
import sys
import tempfile

# Ensure repo root is on sys.path for package import
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Use the public entry point from the package
import src.call_graph_edges as pkg


def run_test(name: str, edge_data: dict) -> tuple[str, str | None, str | None]:
    """Run a single test case. Returns (classification, exception_type, detail)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(edge_data, f)

        try:
            actual = pkg.load_call_edges(filepath)
            return ("not_confirmed", None, f"no exception raised, returned {actual}")
        except Exception as e:
            exc_type = type(e).__name__
            if issubclass(type(e), ValueError):
                return ("not_confirmed_valueerror", exc_type, str(e))
            else:
                return ("confirmed", exc_type, str(e))


def main():
    # Test cases designed to trigger the bug:
    #   invalid edges that should raise ValueError but may raise something else.

    tests = {
        # 1: callee missing entirely -> _edge_from_mapping processes None instead of dict
        "callee_missing": {
            "edges": [
                {
                    "caller": {"fqn": "ns::func"},
                    # callee key intentionally missing
                }
            ]
        },
        # 2: callee is None (not a dict)
        "callee_none": {
            "edges": [
                {
                    "caller": {"fqn": "ns::func"},
                    "callee": None,
                }
            ]
        },
        # 3: callee is empty dict (missing fqn)
        "callee_empty": {
            "edges": [
                {
                    "caller": {"fqn": "ns::func"},
                    "callee": {},
                }
            ]
        },
        # 4: callee is a list (not a dict)
        "callee_list": {
            "edges": [
                {
                    "caller": {"fqn": "ns::func"},
                    "callee": [1, 2, 3],
                }
            ]
        },
        # 5: caller missing
        "caller_missing": {
            "edges": [
                {
                    "callee": {"fqn": "ns::target"},
                }
            ]
        },
        # 6: caller is None
        "caller_none": {
            "edges": [
                {
                    "caller": None,
                    "callee": {"fqn": "ns::target"},
                }
            ]
        },
        # 7: caller is empty dict
        "caller_empty": {
            "edges": [
                {
                    "caller": {},
                    "callee": {"fqn": "ns::target"},
                }
            ]
        },
        # 8: callee fqn is an integer (not a string)
        "callee_fqn_int": {
            "edges": [
                {
                    "caller": {"fqn": "ns::func"},
                    "callee": {"fqn": 42},
                }
            ]
        },
        # 9: callee fqn is a list
        "callee_fqn_list": {
            "edges": [
                {
                    "caller": {"fqn": "ns::func"},
                    "callee": {"fqn": ["not", "a", "string"]},
                }
            ]
        },
        # 10: callsite_names is not a list
        "callsite_not_list": {
            "edges": [
                {
                    "caller": {"callsite_names": "not_a_list"},
                    "callee": {"fqn": "ns::target"},
                }
            ]
        },
        # 11: info_names is not a list
        "info_names_not_list": {
            "edges": [
                {
                    "caller": {"fqn": "ns::func"},
                    "callee": {"fqn": "ns::target", "info_names": "not_a_list"},
                }
            ]
        },
        # 12: callee fqn is empty string
        "callee_fqn_empty": {
            "edges": [
                {
                    "caller": {"fqn": "ns::func"},
                    "callee": {"fqn": ""},
                }
            ]
        },
        # 13: callee fqn is whitespace
        "callee_fqn_whitespace": {
            "edges": [
                {
                    "caller": {"fqn": "ns::func"},
                    "callee": {"fqn": "   "},
                }
            ]
        },
        # 14: caller fqn is non-string (None type)
        "caller_fqn_none": {
            "edges": [
                {
                    "caller": {"fqn": None},
                    "callee": {"fqn": "ns::target"},
                }
            ]
        },
        # 15: edge item itself is a list (not dict)
        "edge_item_is_list": {
            "edges": [
                [1, 2, 3]
            ]
        },
        # 16: edge item itself is None
        "edge_item_is_none": {
            "edges": [
                None
            ]
        },
        # 17: edge item is a string
        "edge_item_is_string": {
            "edges": [
                "not_a_dict"
            ]
        },
        # 18: caller fqn is a bool
        "caller_fqn_bool": {
            "edges": [
                {
                    "caller": {"fqn": True},
                    "callee": {"fqn": "ns::target"},
                }
            ]
        },
    }

    confirmed = []
    not_confirmed = []
    errors = []

    for name, edge_data in tests.items():
        classification, exc_type, detail = run_test(name, edge_data)
        status_line = f"[{classification}] {name}: {detail[:120]}"
        print(status_line)
        if classification.startswith("confirmed"):
            confirmed.append((name, exc_type, detail))
        elif classification == "not_confirmed":
            not_confirmed.append((name, None, detail))
        else:
            not_confirmed.append((name, exc_type, detail))

    print()
    if confirmed:
        print(f"CONFIRMED — {len(confirmed)} test(s) triggered non-ValueError:")
        for name, exc_type, detail in confirmed:
            print(f"  - {name}: {exc_type}: {detail}")
    else:
        print(f"NOT CONFIRMED — All {len(not_confirmed)} exception-raising tests"
              f" caught ValueError (spec-compliant). No non-ValueError leak found.")


if __name__ == "__main__":
    main()
