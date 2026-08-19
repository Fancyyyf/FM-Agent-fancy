import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.trace_writer import write_payload


def probe():
    with tempfile.TemporaryDirectory(prefix="bug_probe-") as tmpdir:
        trace_dir = os.path.join(tmpdir, ".trace")
        payload_dir = os.path.join(trace_dir, "payloads")

        # Use event_id with path traversal characters so that
        # f"{event_id}_{name}" produces standalone ".." components
        # e.g., "{../../}_{hacked}" → "../../_hacked" escapes payload_dir
        event_id = "../../"
        name = "escaped_file"

        try:
            rel_path = write_payload(
                trace_dir=trace_dir,
                event_id=event_id,
                name=name,
                content="malicious content",
            )
        except Exception as e:
            print(f"ERROR: {e}")
            return False

        # Resolve the written file to an absolute path
        written_path = os.path.normpath(os.path.join(os.path.dirname(trace_dir), rel_path))
        payload_dir_real = os.path.realpath(payload_dir)
        written_path_real = os.path.realpath(written_path)

        # Check: is the written file inside the payloads directory?
        inside = written_path_real.startswith(payload_dir_real + os.sep)

        return not inside


if __name__ == "__main__":
    import sys as _sys

    # The package is at the repo root, sys.path already adjusted above
    try:
        bug_reproduced = probe()
        if bug_reproduced:
            print("CONFIRMED — path traversal: file escaped the payload subdirectory")
        else:
            print("NOT CONFIRMED — file remained inside the payload subdirectory")
    except Exception as exc:
        print(f"ERROR: {exc}")
        _sys.exit(1)
