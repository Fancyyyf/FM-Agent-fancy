import sys
import os
import tempfile

# Ensure the repo root is on sys.path so `import main` works
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    # Import _clean_previous_run from the main module (public entry point of FM-Agent)
    # main.py has `if __name__ == "__main__":` guard at line 272, so importing is safe
    import main

    # Create all fixtures in a fresh temporary directory (self-validation guard)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a real target directory with content
        target_dir = os.path.join(tmpdir, "real_target")
        os.makedirs(target_dir)
        marker_file = os.path.join(target_dir, "important_data.txt")
        with open(marker_file, 'w') as f:
            f.write("this should NOT be deleted")

        # Create a symlink to the target directory
        symlink_dir = os.path.join(tmpdir, "work_dir_link")
        os.symlink(target_dir, symlink_dir)

        # Pre-condition: symlink is recognized as a directory by os.path.isdir
        assert os.path.isdir(symlink_dir), (
            "pre-condition failed: os.path.isdir should return True for symlink to dir"
        )

        # Act: call the function under test with the symlink path.
        # Handle both Python versions:
        #   - Python 3.12+: shutil.rmtree raises OSError on symlinks
        #   - Older: shutil.rmtree removes the symlink node itself
        raised = False
        error_msg = ""
        try:
            main._clean_previous_run(symlink_dir)
        except OSError as e:
            raised = True
            error_msg = str(e)

        # Check if the TARGET directory still exists
        target_still_exists = os.path.isdir(target_dir)
        marker_still_there = os.path.isfile(marker_file)

        # The bug: os.path.isdir follows symlinks (returns True for symlink->dir),
        # so _clean_previous_run enters the rmtree branch. But shutil.rmtree does
        # NOT recurse into the symlink target — on Python 3.12+ it raises
        # OSError("Cannot call rmtree on a symbolic link"), and on older Python
        # it just removes the symlink node. In neither case is the target directory
        # or its contents touched, violating the spec.
        bug_confirmed = target_still_exists and marker_still_there

        if bug_confirmed:
            if raised:
                print(
                    'CONFIRMED — shutil.rmtree raised OSError on symlink '
                    f'({error_msg}); target directory and contents untouched '
                    f'at: {target_dir!r}'
                )
            else:
                print(
                    'CONFIRMED — symlink removed but target directory and contents '
                    f'still exist at: {target_dir!r}'
                )
            print(f'  marker file intact: {marker_file!r}')
        else:
            print(
                'NOT CONFIRMED — target directory was removed '
                f'(target_exists={target_still_exists}, marker_exists={marker_still_there})'
            )

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
