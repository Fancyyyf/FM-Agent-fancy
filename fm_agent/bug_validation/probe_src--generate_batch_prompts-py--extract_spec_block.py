import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

try:
    from src.generate_batch_prompts import extract_spec_block
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Trigger condition: The specification requires the file to begin with the
# LINE "<prefix> [SPEC]" — the first line must be exactly that tag, not just
# start with it. The code checks only content.startswith(tag), so it accepts
# content whose first line is "// [SPEC]extra" as a valid spec block start,
# when it should return None.
#
# This test file's first line is "// [SPEC]extra" (not a valid spec start line)
# followed by a closing "// [SPEC]" line. Per spec, this should return None.
# The buggy code returns a non-None block because startswith matches.

test_content = (
    "// [SPEC]extra junk on first line\n"
    "\n"
    "some arbitrary code here\n"
    "\n"
    "// [SPEC]\n"
    "# trailing content\n"
)

with tempfile.NamedTemporaryFile(
    mode="w", suffix=".c", delete=False, encoding="utf-8"
) as tf:
    tf.write(test_content)
    tmp_path = Path(tf.name)

try:
    actual = extract_spec_block(tmp_path)
    # Per spec: file does not begin with a "<prefix> [SPEC]" LINE, so should return None.
    expected = None
    passed = actual != expected
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    tmp_path.unlink(missing_ok=True)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
