import sys
import os
import json
import threading
import tempfile

# Add repo root to sys.path so that `from src import pipeline_setup` works
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src import pipeline_setup
except ImportError as e:
    print(f"ERROR: Cannot import src.pipeline_setup: {e}")
    sys.exit(1)

try:
    # Create a fresh temporary directory for the probe workspace
    tmpdir = tempfile.mkdtemp()
    fifo_path = os.path.join(tmpdir, "phases.json")

    # Create a named pipe (FIFO) — this is NOT a regular file
    os.mkfifo(fifo_path)

    # Valid JSON content that conforms to the phases.json schema
    valid_json = json.dumps({
        "phases": [
            {
                "modules": [
                    {
                        "name": "test_module",
                        "source_files": ["test.py"]
                    }
                ]
            }
        ]
    })

    # Thread synchronisation event for ordered teardown
    writer_done = threading.Event()

    def writer():
        """Write valid schema-conforming JSON into the FIFO."""
        try:
            with open(fifo_path, "w") as f:
                f.write(valid_json)
        except Exception:
            pass
        finally:
            writer_done.set()

    wt = threading.Thread(target=writer, daemon=True)
    wt.start()

    # Call the function under test.
    # _phase_plan_complete opens the FIFO for reading, which unblocks
    # the writer's open-for-write, data flows, and both sides close.
    actual = pipeline_setup._phase_plan_complete(tmpdir)

    # Wait for the writer to finish before cleanup
    writer_done.wait(timeout=10)
    wt.join(timeout=1)

    # Cleanup the FIFO and temporary directory
    try:
        os.unlink(fifo_path)
    except OSError:
        pass
    try:
        os.rmdir(tmpdir)
    except OSError:
        pass

    # The specification says: return False when phases.json is NOT a regular file.
    # A FIFO is NOT a regular file, so the expected (spec-correct) value is False.
    expected = False

    if actual != expected:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
