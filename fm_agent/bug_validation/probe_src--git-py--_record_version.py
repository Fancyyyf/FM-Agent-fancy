import sys
import os
import tempfile

# Add repo root to sys.path so that "import src" resolves
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    import src.git

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            src.git._record_version(123, tmpdir)
        except TypeError as e:
            print(f'CONFIRMED -- TypeError raised: {e} | spec requires str(commit_id) conversion')
            sys.exit(0)

        # If no TypeError, check the file contents
        version_path = os.path.join(tmpdir, "version.log")
        if not os.path.exists(version_path):
            print(f'CONFIRMED -- no version.log created | expected "123\\n"')
            sys.exit(0)

        with open(version_path, "r") as f:
            content = f.read()

        expected = "123\n"
        if content == expected:
            print(f'NOT CONFIRMED -- actual matched expected: {content!r}')
        else:
            print(f'CONFIRMED -- actual: {content!r} | expected: {expected!r}')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
