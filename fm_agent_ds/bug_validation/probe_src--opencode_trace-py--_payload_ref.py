"""Probe for _payload_ref bug: os.path.relpath raises ValueError on cross-drive paths (Windows)."""
import sys
import os
import tempfile
import traceback

# Point sys.path at repo root so "from src import opencode_trace" resolves
# (the public entry point per pyproject.toml's package layout)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)

# ---------- helpers ----------------------------------------------------------
def _test_relpath_direct(trace_dir, path):
    """Test os.path.relpath directly with a given pair of arguments."""
    try:
        result = os.path.relpath(path, os.path.dirname(trace_dir))
        return result, None
    except ValueError as e:
        return None, f"ValueError: {e}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _test_via_public_api():
    """Exercise _payload_ref through record_opencode_call (the public API
    that calls it), using a real temporary directory so file-existence
    checks pass."""
    from src.opencode_trace import record_opencode_call

    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = os.path.join(tmpdir, "work")
        os.makedirs(work_dir, exist_ok=True)

        trace_dir = os.path.join(work_dir, "trace")
        os.makedirs(trace_dir, exist_ok=True)

        payload_dir = os.path.join(trace_dir, "payloads")
        os.makedirs(payload_dir, exist_ok=True)

        log_path = os.path.join(payload_dir, "evt_opencode.log")
        with open(log_path, "w") as f:
            f.write("dummy log")

        trace_path = os.path.join(trace_dir, "opencode", "evt.jsonl")
        os.makedirs(os.path.dirname(trace_path), exist_ok=True)
        with open(trace_path, "w") as f:
            f.write('{"test": true}\n')

        try:
            record_opencode_call(
                work_dir=work_dir,
                event_id="evt",
                stage="test",
                status="success",
                started="2025-01-01T00:00:00Z",
                ended="2025-01-01T00:00:01Z",
                command={"tool": "verify", "prompt_path": "/dev/null"},
                opencode_log_path=log_path,
                opencode_trace_path=trace_path,
            )
            return True, None
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"


# ---------- main -------------------------------------------------------------
def main():
    confirmed = False
    last_error = None

    # ------------------------------------------------------------------
    # Attempt 1 — normal paths (public API via record_opencode_call)
    # ------------------------------------------------------------------
    ok, err = _test_via_public_api()
    if err is not None:
        last_error = err
        if err.startswith("ValueError"):
            confirmed = True
            print(f"CONFIRMED — public API raised ValueError: {err}")
            return
        else:
            print(f"Attempt 1 (public API): unexpected error — {err}")
    else:
        print(f"Attempt 1 (public API): OK — _payload_ref returned a string")

    # ------------------------------------------------------------------
    # Attempt 2 — edge-case paths on Linux (os.path.relpath directly)
    # ------------------------------------------------------------------
    edge_cases = [
        ("cross-filesystem simulation", "/mnt/disk1/trace", "/mnt/disk2/data/file"),
        ("UNC-style double-slash", "//host/share/trace", "/home/user/data"),
        ("root vs relative mix", "/", "relative/path"),
        ("deeply nested", "/a" * 50 + "/trace", "/b" * 50 + "/data"),
        ("symlink-looking", "/tmp/trace/..", "/tmp/../var/data"),
        ("dot-components", "/./tmp/./trace", "/./home/./data"),
    ]
    for desc, td, fp in edge_cases:
        result, verr = _test_relpath_direct(td, fp)
        if verr is not None:
            last_error = f"{desc}: {verr}"
            if verr.startswith("ValueError"):
                confirmed = True
                print(f"CONFIRMED — edge case '{desc}': {verr}")
                return
            else:
                print(f"Attempt 2 ({desc}): unexpected — {verr}")
        else:
            print(f"Attempt 2 ({desc}): OK — result={result!r}")

    # ------------------------------------------------------------------
    # Attempt 3 — empty / null-byte paths (os.path.relpath directly)
    # ------------------------------------------------------------------
    pathological = [
        ("empty path", "/tmp/trace", ""),
        ("empty trace_dir", "", "/tmp/data"),
        ("both empty", "", ""),
    ]
    for desc, td, fp in pathological:
        result, verr = _test_relpath_direct(td, fp)
        if verr is not None:
            last_error = f"{desc}: {verr}"
            if verr.startswith("ValueError"):
                confirmed = True
                print(f"CONFIRMED — pathological input '{desc}': {verr}")
                return
            else:
                print(f"Attempt 3 ({desc}): unexpected — {verr}")
        else:
            print(f"Attempt 3 ({desc}): OK — result={result!r}")

    # ------------------------------------------------------------------
    # Final verdict
    # ------------------------------------------------------------------
    if confirmed:
        print("CONFIRMED — _payload_ref raises ValueError for at least one input")
    else:
        print(
            "NOT CONFIRMED — os.path.relpath does not raise ValueError on Linux "
            "for any tested path combination; the reported cross-drive trigger "
            "is Windows-specific and cannot be reproduced on this platform"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {traceback.format_exc()}")
        sys.exit(1)
