import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

try:
    from src.generate_batch_prompts import extract_info_block
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Trigger condition: The buggy code uses content.find(tag) which matches the
# "# [INFO]" marker as a substring anywhere in the file. Per the spec, the
# marker must appear as a whole line. When "# [INFO]" appears mid-line before
# the first whole-line marker, c.find() picks the mid-line occurrence, causing
# wrong boundary selection.

test_content = (
    "# [SPEC]\n"
    "# Unit: test_file.py\n"
    "# [SPEC]\n"
    "\n"
    "# Some text that mentions # [INFO] here\n"
    "# [INFO]\n"
    "actual info content\n"
    "# [INFO]\n"
)

with tempfile.NamedTemporaryFile(
    mode="w", suffix=".py", delete=False, encoding="utf-8"
) as tf:
    tf.write(test_content)
    tmp_path = Path(tf.name)

try:
    actual = extract_info_block(tmp_path)
    # Spec: text between first whole-line # [INFO] and second whole-line # [INFO]
    # That's between line 7 and line 9 → "actual info content"
    expected = "actual info content"
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
