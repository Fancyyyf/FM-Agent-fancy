import sys
import os
import json
import tempfile

# Add repo root to sys.path so 'src' package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.file_utils import collect_file_names

    tmpdir = tempfile.mkdtemp()
    output_path = os.path.join(tmpdir, "file_list.json")

    # Create a known file in the temp dir so os.walk has something
    with open(os.path.join(tmpdir, "hello.txt"), "w") as f:
        f.write("test")

    try:
        # First call: creates output_path via collect_file_names → _write_file_names
        result1 = collect_file_names(tmpdir, output_path)

        # Manually overwrite output_path with a KNOWN different JSON array
        # This is what _write_file_names should detect and return per spec
        expected = sorted(["alpha", "beta", "gamma"])
        with open(output_path, "w") as f:
            json.dump(expected, f)

        # Read back to confirm it's written correctly
        with open(output_path, "r") as f:
            file_before = json.load(f)

        # Second call: spec says _write_file_names should detect existing valid JSON
        # and return it unmodified. Buggy code will overwrite with re-walked list.
        result2 = collect_file_names(tmpdir, output_path)

        # Read file content after the second call
        with open(output_path, "r") as f:
            file_after = json.load(f)

        # The bug: result2 should == expected, but code returns walk results
        # Also: file_after should == expected, but code overwrites
        bug_present = (result2 != expected) or (file_after != expected)

    finally:
        # Cleanup
        import shutil
        shutil.rmtree(tmpdir)

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)

if bug_present:
    print(f"CONFIRMED — result2: {json.dumps(result2)} | file_after: {json.dumps(file_after)} | expected: {json.dumps(expected)}")
else:
    print(f"NOT CONFIRMED — result2 == expected == {json.dumps(result2)}")
