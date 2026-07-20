import sys, os, tempfile, shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.trace_writer import write_payload

    tmpdir = tempfile.mkdtemp()
    orig_cwd = os.getcwd()

    try:
        os.chdir(tmpdir)

        # Call write_payload with trace_dir=".", the trigger condition
        result = write_payload(".", "evt1", "test", "hello")

        # The spec says the returned path must be relative to
        # "the directory one level above trace_dir".
        # For trace_dir=".", one level above is "..", whose absolute path
        # is os.path.dirname(tmpdir).
        #
        # Expected: relpath from parent-of-trace_dir to the written file
        expected = os.path.relpath(
            os.path.join(tmpdir, "payloads", "evt1_test"),
            os.path.dirname(tmpdir),
        )

        # Bug check: the actual result is relative to os.path.dirname(".")
        # which is "" (effectively "." / same as trace_dir), NOT "..".
        passed = result != expected

        if passed:
            print(f"CONFIRMED — actual: {result!r} | expected: {expected!r}")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {result!r}")
    finally:
        os.chdir(orig_cwd)
        shutil.rmtree(tmpdir, ignore_errors=True)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
