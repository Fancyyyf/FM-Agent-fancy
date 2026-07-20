import sys

try:
    from src.generate_batch_prompts import phase_callee_info_names_key

    # The exact target key for phase=1 ("phase1_callee_info_names_by_caller")
    # is NOT in the dict, so the code enters the iteration loop.
    # The int key 1 appears BEFORE the matching string key.
    # Per spec: should find "phase0_callee_info_names_by_caller" (starts with
    # "phase", ends with "_callee_info_names_by_caller") and return it.
    # Per buggy code: crashes with AttributeError on int key 1.
    func = {1: "value", "phase0_callee_info_names_by_caller": "matching"}
    phase = 1

    expected = "phase0_callee_info_names_by_caller"
    actual = phase_callee_info_names_key(func, phase)

    # If we reach here, the code didn't crash. Bug is reproduced if
    # the returned value doesn't match the expected spec-correct output.
    passed = actual != expected

except AttributeError as e:
    # Bug CONFIRMED: crashed on non-string key when it should return a value
    print(f"CONFIRMED — AttributeError on non-string key: {e}")
    sys.exit(0)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
