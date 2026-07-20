import sys
import os

# Add repo root to sys.path so the 'src' package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.call_graph_edges import normalize_fqn_label

    # Input from trigger_condition: '"hello"' (outer double-quotes, inner single-quoted hello)
    # In Python literal: '\'"hello"\''
    input_label = "'\"hello\"'"

    # First application
    result1 = normalize_fqn_label(input_label)

    # Second application (on the output of the first call, testing idempotence)
    result2 = normalize_fqn_label(result1)

    # Idempotence requires result1 == result2
    # The bug: _clean_label only strips quotes once, so nested quotes survive the first call
    bug_reproduced = result1 != result2

    if bug_reproduced:
        print(f"CONFIRMED — idempotence violated:")
        print(f"  input:     {input_label!r}")
        print(f"  1st call:  {result1!r}")
        print(f"  2nd call:  {result2!r}")
        print(f"  expected (idempotent): both calls produce the same output")
    else:
        print(f"NOT CONFIRMED — result1 == result2 == {result1!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
