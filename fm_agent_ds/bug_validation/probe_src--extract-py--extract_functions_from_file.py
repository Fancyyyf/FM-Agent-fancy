import sys
import os
import tempfile

# Add repo root to path so we can import src.extract
repo_root = '/home/fancy/Projects_Vault/FM-Agent'
sys.path.insert(0, repo_root)

try:
    from src.extract import extract_functions_from_file
except Exception as e:
    print(f'ERROR (import): {e}')
    sys.exit(1)

# Create a temporary test file with a literal CR byte (0x0D) inside a string.
# The CR byte is part of the source content, NOT a line ending.
tmpdir = tempfile.mkdtemp()
test_file = os.path.join(tmpdir, 'test_cr_in_string.py')

# Write a valid Python file where one line contains a literal CR byte inside a
# string at the end of the line (right before the closing quote + newline).
# This CR byte is content, not a line ending, and should be preserved.
with open(test_file, 'wb') as f:
    f.write(b'def func_with_cr():\n')
    # The \x0d is a literal carriage return byte inside the string.
    # This line reads: '    return "prefix' + CR + '"\n'
    f.write(b'    return "prefix\x0d"\n')

try:
    results = extract_functions_from_file(test_file, 'python')
    source_text = results[0][1]  # The source text for func_with_cr

    # The spec says source_text should preserve content, normalizing only
    # line endings. A literal CR byte that is part of the source content
    # must not be stripped.
    # Check whether the CR byte (\x0d) survived in the output.
    if b'\x0d' not in source_text.encode('utf-8', errors='surrogateescape'):
        print(
            'CONFIRMED'
            ' — CR byte stripped from function body. '
            f'actual: {source_text!r}'
        )
    else:
        print(
            'NOT CONFIRMED'
            f' — CR byte preserved in function body: {source_text!r}'
        )

finally:
    # Clean up the temp directory
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
