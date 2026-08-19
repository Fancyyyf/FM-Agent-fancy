# Bug Report: _clean_previous_run

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/main-py/_clean_previous_run.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

The filesystem path denoted by work_dir no longer refers to an existing directory. If the path referred to a directory before the call, that directory and all files and subdirectories within it have been recursively removed from the filesystem.

---

### Actual Behavior

If the function completes without raising an exception, then the following holds: if `os.path.isdir(work_dir)` was true before the call, then `os.path.exists(work_dir)` is false after the call (the directory and its contents have been removed); if `work_dir` was not a directory (or did not exist), the filesystem state at `work_dir` is unchanged. If the function raises an exception, the state of `work_dir` is unspecified (may be partially removed or unchanged). Formally: \\( (\\text{normal\\_return} \\Rightarrow (\\text{is\\_dir}(work_dir)_{\\text{pre}} \\Rightarrow \\neg \\text{exists}(work_dir)_{\\text{post}}) \\wedge (\\neg \\text{is\\_dir}(work_dir)_{\\text{pre}} \\Rightarrow \\text{unchanged}(work_dir)) ) \\wedge (\\text{exceptional\\_return} \\Rightarrow \\top ) \\)

---

## Code Evidence

```
Line 3:     if os.path.isdir(work_dir):
Line 4:         shutil.rmtree(work_dir)
```

---

## Trigger Condition

os.path.isdir follows symlinks, so a symlink to a directory is considered a directory and the condition is true. However, shutil.rmtree removes the symlink itself, not the target directory. The target directory and its contents remain, violating the requirement that the directory and all its contents are recursively removed.

---

## How to trigger the bug

When `work_dir` is a symlink pointing to a real directory, `os.path.isdir(work_dir)` returns `True` (because it follows symlinks), so the function enters the `shutil.rmtree` branch. However, `shutil.rmtree` does not recurse into the symlink target:

- On **Python 3.12+**: `shutil.rmtree` raises `OSError: Cannot call rmtree on a symbolic link`. The target directory and its contents are left completely untouched.
- On **older Python**: `shutil.rmtree` removes the symlink node itself but does not touch the target directory or its contents.

In both cases, the target directory and all its files/subdirectories remain on disk, violating the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `work_dir` | A path that is a symlink pointing to an existing directory containing files |

### Expected (spec-correct) Output

The target directory (to which `work_dir` points) and all files and subdirectories within it are recursively removed from the filesystem.

### Actual (buggy) Output

On Python 3.12+: `OSError: Cannot call rmtree on a symbolic link` is raised. The target directory and all its contents remain intact on disk.

On older Python: The symlink itself is removed. The target directory and all its contents remain intact on disk.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import main

# Create a real directory with content
os.makedirs("/tmp/test_target", exist_ok=True)
with open("/tmp/test_target/data.txt", "w") as f:
    f.write("important data")

# Create a symlink to it
os.symlink("/tmp/test_target", "/tmp/test_link")

# Call _clean_previous_run with the symlink
main._clean_previous_run("/tmp/test_link")
# On Python 3.12+: raises OSError: Cannot call rmtree on a symbolic link
# On older Python: removes /tmp/test_link (the symlink), but /tmp/test_target

# Check: the target directory still exists with its contents
print(os.path.isdir("/tmp/test_target"))   # True — BUG: should be False
print(os.path.isfile("/tmp/test_target/data.txt"))  # True — BUG: should be False
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Ensure the repo root is on sys.path so `import main` works
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import main

    # Create all fixtures in a fresh temporary directory (self-validation guard)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a real target directory with content
        target_dir = os.path.join(tmpdir, "real_target")
        os.makedirs(target_dir)
        marker_file = os.path.join(target_dir, "important_data.txt")
        with open(marker_file, 'w') as f:
            f.write("this data should NOT be deleted")

        # Create a symlink to the target directory
        symlink_dir = os.path.join(tmpdir, "work_dir_link")
        os.symlink(target_dir, symlink_dir)

        # Pre-condition: symlink is recognized as a directory by os.path.isdir
        assert os.path.isdir(symlink_dir), (
            "pre-condition failed: os.path.isdir should return True for symlink to dir"
        )
        assert os.path.isdir(target_dir), "target dir should exist before the call"

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
```

### Probe Output

```
CONFIRMED — shutil.rmtree raised OSError on symlink (Cannot call rmtree on a symbolic link); target directory and contents untouched at: '/tmp/tmpj6g9l18x/real_target'
  marker file intact: '/tmp/tmpj6g9l18x/real_target/important_data.txt'
```
