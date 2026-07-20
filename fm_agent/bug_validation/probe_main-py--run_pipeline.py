import sys
import os
import tempfile

# Ensure repo root is on sys.path so we can import main
repo_root = os.getcwd()
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from main import run_pipeline

    # Create a temp directory with no supported source files (only .txt)
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "readme.txt"), "w") as f:
            f.write("This is not a source file.\n")

        bug_confirmed = False
        try:
            run_pipeline(tmpdir)
        except SystemExit as e:
            # sys.exit(1) was called — the spec says graceful early return
            # but the code terminates the process with sys.exit(1)
            bug_confirmed = True

        if bug_confirmed:
            print("CONFIRMED — run_pipeline called sys.exit(1) instead of returning early when no supported source files found")
        else:
            print("NOT CONFIRMED — run_pipeline returned gracefully")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
