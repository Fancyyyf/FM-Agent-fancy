import sys
import os

# Ensure repo root is on sys.path so 'src' and 'config' are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.pipeline_setup import _merge_descriptions

    # Trigger condition: neither description is empty and source_desc is not a substring of target_desc.
    # Spec says: join with a single space
    # Code (line 37): joins with "\n\n"
    target = "Module Alpha handles imports"
    source = "Module Beta handles exports"

    actual = _merge_descriptions(target, source)
    expected = "Module Alpha handles imports Module Beta handles exports"  # single space per spec

    # Bug is confirmed if actual does NOT match what the spec requires (the code uses \n\n instead of space)
    passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
