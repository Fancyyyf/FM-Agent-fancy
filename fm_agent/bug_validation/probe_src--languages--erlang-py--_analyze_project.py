"""Probe script for bug: _analyze_project returns cached data without ELP check."""
import os
import sys
import tempfile

# Ensure the src directory is importable
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    from languages import erlang
except ImportError as e:
    print(f"ERROR: Failed to import erlang module: {e}")
    sys.exit(1)


def main():
    # Create an empty temp directory as the fake Erlang project
    tmpdir = tempfile.mkdtemp(prefix="erlang_probe_")
    abs_tmpdir = os.path.abspath(tmpdir)

    try:
        # Step 1: Compute the fingerprint that the real function would use
        fingerprint = erlang._project_fingerprint(tmpdir)
        print(f"[DEBUG] Fingerprint for empty dir: {fingerprint}")

        # Step 2: Manually seed the in-memory cache — simulating a previous
        #          successful ELP run that populated the cache
        mock_analysis = erlang.ErlangAnalysis(functions={}, edges={}, spans={})
        erlang._CACHE[abs_tmpdir] = (fingerprint, mock_analysis)
        print(f"[DEBUG] Cache seeded for {abs_tmpdir}")

        # Step 3: Break ELP by pointing to a nonexistent binary
        os.environ["ELP_COMMAND"] = "/nonexistent/elp_probe_fake_binary"
        print(f"[DEBUG] ELP_COMMAND set to nonexistent binary")

        # Step 4: Call _analyze_project — spec says it should raise an exception
        #         when ELP is unavailable, but the code returns cached data instead
        result = erlang._analyze_project(tmpdir)

        # If we reach here without an exception, the cache was used and ELP was
        # never contacted. This violates the spec: "Raises an exception when the
        # ELP backend is unavailable or analysis cannot complete."
        print(
            f"CONFIRMED — cached result returned without ELP availability check "
            f"(functions={len(result.functions)}, edges={len(result.edges)})"
        )
    except Exception as exc:
        print(f"NOT CONFIRMED — exception raised: {exc.__class__.__name__}: {exc}")
    finally:
        # Cleanup
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass


if __name__ == "__main__":
    main()
