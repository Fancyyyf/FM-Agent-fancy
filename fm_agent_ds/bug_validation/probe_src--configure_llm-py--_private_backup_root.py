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
