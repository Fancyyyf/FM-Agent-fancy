# Bug Report: backup_file

**Source file:** `src/configure_llm.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When path does not exist, returns None without modifying the filesystem. When path exists and is readable, returns a Path identifying a newly created regular file whose content is byte-for-byte identical to the content of the file at path at the time of the call. The backup file is created in the same directory as path when private is false, and in a private backup directory with owner-restricted permissions when private is true. When path.name is '.env', the backup file permissions restrict read and write access to the owner regardless of the private flag. When private is true, the backup file permissions likewise restrict read and write access to the owner. Every call produces a distinct backup destination  no existing backup file is overwritten. When a filesystem operation after destination reservation fails, the reserved empty destination file is removed before the exception propagates to the caller.

---

### Actual Behavior

If path does not exist, the function returns None without filesystem changes. If path exists, the function creates a unique backup file named using a timestamp (now or current time) and a disambiguation counter; the backup is created exclusively with mode 0o600 if private is True or path.name == '.env', else 0o644. On successful copy (shutil.copy2), permissions are forced to 0o600 for sensitive sources, and the backup path is returned. If the copy fails, the backup is removed (best-effort) and the exception is re-raised; other exceptions (e.g., from directory creation or exclusive file creation) propagate without cleanup. Formally: (path.exists()  return = None  filesystem unchanged)  (path.exists()  ! backup such that (backup created  (copy succeeds  return = backup  backup is copy of path with forced permissions)  (copy fails  (unlink(backup) attempted; exception re-raised)))).

---

## Code Evidence

Line 42:     if private or path.name == ".env":
Line 43:         backup.chmod(0o600)

---

## Trigger Condition

The specification requires that when a filesystem operation after destination reservation fails, the reserved empty destination file is removed before the exception propagates. The code only wraps shutil.copy2 in a try/except that performs cleanup; the subsequent chmod for sensitive files (private or .env) is outside that protection. If that chmod fails, the exception propagates without unlinking the backup file, leaving an empty file on disk.

---

## How to trigger the bug

The `backup.chmod(0o600)` call on line 656 of `src/configure_llm.py` sits outside the `try/except` block that guards `shutil.copy2`. When `shutil.copy2` succeeds (the backup file now contains the copied data) but the subsequent `chmod` fails, the exception propagates to the caller without cleaning up the backup file, leaving it orphaned on disk.

### Inputs

| Parameter | Value |
|-----------|-------|
| `path` | `Path("<tmpdir>/.env")` (an existing regular file) |
| `private` | `False` (sensitive-files path triggers the chmod regardless) |
| `now` | (default: `datetime.now()`) |

### Expected (spec-correct) Output

The backup file should be removed from disk and the exception should propagate to the caller. No `.env.bak.*` file should remain.

### Actual (buggy) Output

The backup file (e.g., `.env.bak.20260728-001205`) is left on disk after the `chmod` raises `OSError`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from pathlib import Path
from unittest.mock import patch
from src.configure_llm import backup_file

def failing_chmod(self, mode):
    raise OSError(13, "Permission denied")

with tempfile.TemporaryDirectory() as tmpdir:
    test_file = Path(tmpdir) / ".env"
    test_file.write_text("test content")
    with patch.object(Path, "chmod", failing_chmod):
        try:
            backup_file(test_file, private=False)
        except OSError:
            orphans = list(Path(tmpdir).glob(".env.bak.*"))
            # orphans will be non-empty — the backup was not cleaned up
            print("orphans:", orphans)
# actual (buggy) output: ['<tmpdir>/.env.bak.20260728-001205']
# expected (correct) output: []
```

---

## Probe Script

```python
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "/home/fancy/Projects_Vault/FM-Agent")

try:
    from src.configure_llm import backup_file
except Exception as e:
    print(f"ERROR: import failed: {e}")
    sys.exit(1)

def failing_chmod(self, mode):
    raise OSError(13, "Permission denied")

try:
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / ".env"
        test_file.write_text("test content")

        with patch.object(Path, "chmod", failing_chmod):
            try:
                backup_file(test_file, private=False)
            except OSError:
                # After the chmod failure, check for orphaned backup file(s).
                orphans = sorted(Path(tmpdir).glob(".env.bak.*"))
                if orphans:
                    print(
                        "CONFIRMED — orphaned backup left on disk:",
                        [str(p.name) for p in orphans],
                    )
                else:
                    print("NOT CONFIRMED — no orphaned backup found after chmod failure")
            else:
                print("NOT CONFIRMED — backup_file did not raise after chmod failure")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — orphaned backup left on disk: ['.env.bak.20260728-001205']
```
