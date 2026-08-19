"""Probe script for _project_fingerprint content-blindness bug.

Bug: _project_fingerprint uses only (size, mtime_ns) to detect file changes.
A content modification that preserves file size and mtime_ns escapes detection.
"""
import os
import sys
import tempfile

# Import the module via its public entry point.
# Must add repo root to sys.path so that 'src.languages.erlang' resolves.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from src.languages.erlang import _project_fingerprint

try:
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an Erlang source file inside temp dir
        src_file = os.path.join(tmpdir, "module.erl")
        content_a = "-module(module).\n-export([f/1]).\n\nf(X) -> X + 1.\n"
        with open(src_file, "w") as f:
            f.write(content_a)

        # Record first fingerprint
        fp1 = _project_fingerprint(tmpdir)
        records1 = fp1[1]  # tuple of (rel_path, size, mtime_ns)

        # Capture original mtime_ns before modification
        stat1 = os.stat(src_file)

        # Modify file content but keep exact same byte length
        content_b = "-module(module).\n-export([f/1]).\n\nf(X) -> X * 1.\n"
        # Ensure same length
        assert len(content_a.encode("utf-8")) == len(content_b.encode("utf-8")), \
            f"Content lengths differ: {len(content_a)} vs {len(content_b)}"

        with open(src_file, "w") as f:
            f.write(content_b)

        # Restore original mtime_ns so that size + mtime match the first call
        os.utime(src_file, ns=(stat1.st_atime_ns, stat1.st_mtime_ns))

        # Record second fingerprint
        fp2 = _project_fingerprint(tmpdir)
        records2 = fp2[1]

        # Verify: size and mtime are identical
        stat2 = os.stat(src_file)

        # Check if fingerprint is identical despite different content
        if fp1 == fp2:
            print(
                f"CONFIRMED — fingerprints equal despite content change: "
                f"fp1==fp2, size={stat1.st_size}=={stat2.st_size}, "
                f"mtime_ns={stat1.st_mtime_ns}=={stat2.st_mtime_ns}, "
                f"but content differs"
            )
        else:
            print(
                f"NOT CONFIRMED — fingerprints differ after content change: "
                f"fp1 != fp2"
            )

except AssertionError as e:
    print(f"NOT CONFIRMED — probe assertion failed: {e}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
