"""Probe script for bug: _load_sidecar_json does not catch UnicodeDecodeError.

Spec claim: Returns None if file contents are not valid JSON.
Actual: UnicodeDecodeError (from invalid UTF-8) is not caught — propagates.
"""
import os
import sys
import tempfile
import traceback

# When this script is run via `python3 fm_agent/bug_validation/probe_...py`,
# Python adds the script's directory to sys.path[0], not the repo root.
# Add the project root explicitly so `from src.parser` works.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    # ------------------------------------------------------------------
    # 1. Create a temp directory with a valid source file + bad sidecar
    # ------------------------------------------------------------------
    tmpdir = tempfile.mkdtemp(prefix="bv_probe_")
    src_path = os.path.join(tmpdir, "test_func.py")
    sidecar_path = src_path + ".spec.json"

    # Valid source file — parse_input_function needs it to exist
    with open(src_path, "w", encoding="utf-8") as f:
        f.write("pass\n")

    # Invalid UTF-8 bytes — 0xFF is never valid in UTF-8.
    # _load_sidecar_json opens this with encoding="utf-8", so open()
    # raises UnicodeDecodeError, which is NOT in the caught tuple
    # `(OSError, json.JSONDecodeError)`.
    with open(sidecar_path, "wb") as f:
        f.write(b"\xff\xfe")

    # ------------------------------------------------------------------
    # 2. Call the public entry point that exercises _load_sidecar_json
    # ------------------------------------------------------------------
    from src.parser import parse_input_function

    spec_claims_none = (
        "Spec: Returns None if the file contents are not valid JSON. "
        "Invalid UTF-8 is not valid JSON, so None is expected."
    )

    error_propagated = False
    error_type = None

    try:
        _ = parse_input_function(src_path)
    except UnicodeDecodeError:
        error_propagated = True
        error_type = "UnicodeDecodeError"
    except Exception as e:
        error_propagated = True
        error_type = type(e).__name__

    # ------------------------------------------------------------------
    # 3. Verdict
    # ------------------------------------------------------------------
    # The spec says "returns None" for invalid JSON content.
    # If the code propagates an exception instead, the bug is CONFIRMED.
    if error_propagated:
        print(
            f"CONFIRMED — {error_type} propagated instead of returning None "
            f"when loading a sidecar file with invalid UTF-8. "
            f"({spec_claims_none})"
        )
    else:
        print(
            "NOT CONFIRMED — parse_input_function did not propagate "
            "UnicodeDecodeError for invalid UTF-8 sidecar"
        )

except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
finally:
    # Cleanup temp directory
    try:
        if "tmpdir" in locals() and os.path.isdir(tmpdir):
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass
