"""Probe script for bug: _load_json_edges — attempt 3: boundary cases."""
import sys
import os
import json
import tempfile

try:
    import src.call_graph_edges as cge

    # Attempt 3: test boundary cases that might bypass string validation
    test_cases = [
        ("caller_fqn_bool", [{"caller": {"fqn": True}, "callee": {"fqn": "ok"}}]),
        ("caller_fqn_list", [{"caller": {"fqn": ["a"]}, "callee": {"fqn": "ok"}}]),
        ("callee_missing_key", [{"caller": {"fqn": "x"}, "x": "y"}]),
        ("caller_all_whitespace", [{"caller": {"fqn": "  ", "callsite_names": ["  "]}, "callee": {"fqn": "ok"}}]),
        ("no_caller_key", [{"callee": {"fqn": "ok"}}]),
        ("callee_no_fqn_key", [{"caller": {"fqn": "x"}, "callee": {}}]),
    ]

    bug_confirmed = False
    trig_name = None
    trig_detail = None

    for name, edges_payload in test_cases:
        payload = {"edges": edges_payload}
        buggy_json = json.dumps(payload)

        fd, tmp_path = tempfile.mkstemp(suffix='.json')
        try:
            os.write(fd, buggy_json.encode())
            os.close(fd)

            raised_error = None
            actual_list = None

            try:
                actual_list = cge.load_call_edges(tmp_path)
            except ValueError as e:
                raised_error = str(e)
            except Exception as e:
                print(f'ERROR [{name}]: {type(e).__name__}: {e}')
                sys.exit(1)

            if actual_list is not None:
                for i, edge in enumerate(actual_list):
                    callee_empty = not edge.callee.fqn
                    caller_empty = (not edge.caller.fqn
                                    and not edge.caller.callsite_names)
                    if callee_empty or caller_empty:
                        bug_confirmed = True
                        trig_name = name
                        trig_detail = (
                            f'Invalid CallEdge[{i}]: '
                            f'callee.fqn={edge.callee.fqn!r}, '
                            f'caller.fqn={edge.caller.fqn!r}, '
                            f'caller.callsite_names={edge.caller.callsite_names!r}'
                        )
                        break
                if bug_confirmed:
                    break
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    if bug_confirmed:
        print(f'CONFIRMED — [{trig_name}]: {trig_detail} | expected: ValueError or valid CallEdge')
    else:
        print('NOT CONFIRMED — all boundary cases raised ValueError before returning invalid CallEdge')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
