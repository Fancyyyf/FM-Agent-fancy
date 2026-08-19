"""
Probe script for bug src--extract-py--_function_spans
Tests whether _function_spans preserves trailing newline characters
when the source file uses CRLF line endings.
"""
import sys
import os
import tempfile

try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from src.extract import _function_spans

    # Create a temporary file with \r\n line endings in a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test_probe.py")
        with open(test_file, "wb") as f:
            f.write(b"class Foo:\r\n")
            f.write(b"    def bar(self):\r\n")
            f.write(b"        pass\r\n")

        # Call _function_spans with proj_dir=None to avoid codegraph path
        spans, raw_lines = _function_spans(test_file, "python", proj_dir=None)

        # Check if raw_lines preserves the original \r\n endings
        has_crlf = any(line.endswith('\r\n') for line in raw_lines)

        # The spec claims raw_lines should preserve trailing newline characters.
        # Universal newline translation (no newline='') converts \r\n -> \n.
        # So the buggy behavior means NO raw_lines have \r\n.
        if has_crlf:
            print(f"NOT CONFIRMED — raw_lines preserved \\r\\n ending: {[repr(l) for l in raw_lines]}")
        else:
            print(f"CONFIRMED — raw_lines lost \\r\\n (universal newline translation): {[repr(l) for l in raw_lines]}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
