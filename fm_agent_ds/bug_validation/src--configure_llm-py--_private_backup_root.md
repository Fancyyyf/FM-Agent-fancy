# Bug Report: _private_backup_root

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/configure_llm-py/_private_backup_root.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a Path within the platform's temporary-file directory whose final component encodes the calling process's user identity. The returned path is a directory location, not a file. The user-identity component contains only the characters AZ, az, 09, '.', '\_', and '-'. The same user identity always produces the same path; distinct user identities produce distinct paths.

---

### Actual Behavior

The function returns a `pathlib.Path` object. Let `temp_dir = tempfile.gettempdir()`. The user component `user_component` is determined as: if `hasattr(os, 'getuid')` then `user_component = 'uid-' + str(os.getuid())`; else if `os.environ.get('USERNAME')` is a non-empty string then that value; else if `os.environ.get('USER')` is a non-empty string then that value; else `'user'`. Then `safe = re.sub(r'[^A-Za-z0-9._-]+', '_', user_component).strip('._-') or 'user'`. The returned value is `Path(temp_dir) / f'fm-agent-config-backups-{safe}'`. No filesystem changes occur. Formal: $result = Path(tempfile.gettempdir()) / 'fm-agent-config-backups-' + safe, where safe is derived from the user identity as described, and safe is a non-empty string matching `[A-Za-z0-9._-]+` with no leading/trailing `._-` (or `'user'` as fallback).

---

## Code Evidence

Line 5: user_component = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
Line 6: safe = re.sub(r"[^A-Za-z0-9._-]+", "\_", user_component).strip(".\_-") or "user"

---

## Trigger Condition

The mapping from user_component to safe is not injective; different inputs (e.g., containing backslash vs underscore) can yield the same safe string, causing two distinct user identities to produce identical paths.

---

## How to trigger the bug

The regex `re.sub(r"[^A-Za-z0-9._-]+", "_", user_component)` collapses any sequence of one or more characters outside the allowed set `[A-Za-z0-9._-]` into a single underscore. Because the `+` quantifier matches contiguous runs, two distinct usernames that differ only in which disallowed characters they contain — and where those characters run together — can map to the same safe component. For example, `DOMAIN\user123` and `DOMAIN/user123` both sanitise to `DOMAIN_user123`, producing identical backup-root paths.

### Inputs

| Parameter | Value |
|-----------|-------|
| `os.environ["USERNAME"]` (test 1) | `DOMAIN\user123` |
| `os.environ["USERNAME"]` (test 2) | `DOMAIN/user123` |
| `os.environ["USERNAME"]` (test 3) | `DOMAIN_user123` |

### Expected (spec-correct) Output

Three distinct paths, one for each distinct user identity.

### Actual (buggy) Output

All three usernames produce the same path: `/tmp/fm-agent-config-backups-DOMAIN_user123`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
from src.configure_llm import _private_backup_root

# Force the non-getuid code path (only reachable on platforms without os.getuid).
os.__dict__.pop("getuid", None)

os.environ["USERNAME"] = r"DOMAIN\user123"
path1 = _private_backup_root()  # -> /tmp/fm-agent-config-backups-DOMAIN_user123

os.environ["USERNAME"] = "DOMAIN/user123"
path2 = _private_backup_root()  # -> /tmp/fm-agent-config-backups-DOMAIN_user123 (same)

assert path1 == path2  # spec requires distinct paths — assertion fails
# actual (buggy) output: path1 == path2 == path3
# expected (correct) output: path1 != path2 != path3
```

---

## Probe Script

```python
"""Probe for bug: _private_backup_root non-injective user-identity sanitisation.

Bug ID: src--configure_llm-py--_private_backup_root

The spec requires distinct user identities to produce distinct paths, but the
regex ``re.sub(r"[^A-Za-z0-9._-]+", "_", user_component)`` collapses any
sequence of one or more disallowed characters into a single underscore.  As a
result, different usernames (e.g. "DOMAIN\\user123" vs "DOMAIN/user123") map to
the same safe component and therefore the same backup-root path.

Approach (attempt 1): force the non-getuid code path by temporarily removing
``os.getuid`` from the module namespace, inject two different ``USERNAME``
values whose sanitised forms collide, and assert that the function returns
identical paths.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the project root is importable
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# All probe workspace I/O stays inside a fresh temporary directory.
_probe_work = Path(tempfile.mkdtemp(prefix="probe_backup_root_"))

# Save state we're about to mutate.
_orig_cwd = os.getcwd()
_getuid_entry = os.__dict__.get("getuid")
_saved_username = os.environ.get("USERNAME")
_saved_user = os.environ.get("USER")

try:
    os.chdir(str(_REPO_ROOT))

    # ----------------------------------------------------------------
    # Force the non-getuid code path so that USERNAME is the identity.
    # ----------------------------------------------------------------
    os.__dict__.pop("getuid", None)

    from src.configure_llm import _private_backup_root

    # --- Test 1: backslash in username ---
    os.environ["USERNAME"] = r"DOMAIN\user123"
    path1 = _private_backup_root()

    # --- Test 2: forward slash in username ---
    os.environ["USERNAME"] = "DOMAIN/user123"
    path2 = _private_backup_root()

    # --- Test 3: underscore in username (already-safe form of #1 and #2) ---
    os.environ["USERNAME"] = "DOMAIN_user123"
    path3 = _private_backup_root()

    all_same = path1 == path2 == path3

    if all_same:
        safe = path1.name.replace("fm-agent-config-backups-", "")
        print(
            "CONFIRMED — _private_backup_root produces identical paths for "
            "distinct usernames because the sanitisation regex is non-injective.\n"
            f"  username r'DOMAIN\\\\user123' -> safe: {safe!r}\n"
            f"  username  'DOMAIN/user123'  -> safe: {safe!r}\n"
            f"  username  'DOMAIN_user123'  -> safe: {safe!r}\n"
            f"  Result path: {path1}\n"
            "  Specification requires distinct user identities to produce distinct paths."
        )
    else:
        print(
            "NOT CONFIRMED — distinct usernames produced different paths.\n"
            f"  r'DOMAIN\\\\user123' -> {path1}\n"
            f"   'DOMAIN/user123'  -> {path2}\n"
            f"   'DOMAIN_user123'  -> {path3}"
        )

except Exception as e:
    import traceback

    traceback.print_exc()
    print(f"ERROR: {e}")

finally:
    os.chdir(_orig_cwd)
    # Restore os.getuid entry
    if _getuid_entry is not None:
        os.__dict__["getuid"] = _getuid_entry
    # Restore environment
    if _saved_username is not None:
        os.environ["USERNAME"] = _saved_username
    else:
        os.environ.pop("USERNAME", None)
    if _saved_user is not None:
        os.environ["USER"] = _saved_user
    else:
        os.environ.pop("USER", None)
    shutil.rmtree(_probe_work, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — _private_backup_root produces identical paths for distinct usernames because the sanitisation regex is non-injective.
  username r'DOMAIN\\user123' -> safe: 'DOMAIN_user123'
  username  'DOMAIN/user123'  -> safe: 'DOMAIN_user123'
  username  'DOMAIN_user123'  -> safe: 'DOMAIN_user123'
  Result path: /tmp/fm-agent-config-backups-DOMAIN_user123
  Specification requires distinct user identities to produce distinct paths.
```
