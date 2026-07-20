import sys
import os

# The package is not installed; add repo root to sys.path so "import src" works.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ── Monkey-patch os.path.relpath to simulate Windows cross-drive ValueError ──
# On Windows, os.path.relpath raises ValueError when path and start are on
# different drives. On Linux this cannot happen naturally, so we inject the
# same error to prove the code path is unguarded.
_original_relpath = os.path.relpath

def _cross_drive_relpath(path, start):
    raise ValueError("path is on mount 'D:', start on mount 'C:'")

os.path.relpath = _cross_drive_relpath

try:
    # ── Import via the package's public entry point ──
    from src.languages.codegraph import CodeGraphExtractor

    # Create an extractor with a fake db path.  The ValueError fires at
    # line 278 (os.path.relpath) before sqlite3.connect is ever reached,
    # so the database file does not need to exist.
    extractor = CodeGraphExtractor("/fake/project/.codegraph/codegraph.db")

    # lang_key "python" is supported (_CG_LANG contains it), so the early
    # return at line 272-273 is skipped.  abs_filepath is on a different
    # "drive" (simulated), triggering ValueError from our monkey-patch.
    actual = extractor.get_function_spans("python", "/D:/other/file.py")

    # If we reach this line, the ValueError was handled internally.
    # The spec says: return None when the file is not in the index.
    # So if we got None, the code behaves correctly in this scenario.
    expected = None
    if actual is None:
        print("NOT CONFIRMED — function returned None as expected by spec")
    else:
        print(f"CONFIRMED — expected None (spec: return None for file not in index), got: {actual!r}")

except ValueError as e:
    # ── BUG CONFIRMED ──
    # The spec requires returning None when the file is not in the codegraph
    # index, but os.path.relpath on line 278 raises ValueError on Windows
    # when abs_filepath is on a different drive than root (derived from
    # self._db).  The exception propagates uncaught.
    print(f"CONFIRMED — ValueError raised instead of returning None")
    print(f"Exception: {e}")
    print(f"Expected (spec): None")
    print(f"Actual (buggy): ValueError propagates unhandled from os.path.relpath")
    sys.exit(0)

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)

finally:
    # Restore the original function so the process can exit cleanly.
    os.path.relpath = _original_relpath
