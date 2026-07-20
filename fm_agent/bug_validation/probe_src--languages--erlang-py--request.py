"""Probe script for bug: request() sends list as JSON-RPC params array instead of object."""
import os
import sys

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
    # Create an ElpClient without starting an ELP subprocess
    # Set a tiny timeout so _wait_for_response fails fast
    client = erlang.ElpClient("/tmp")
    client.timeout = 0.001

    # Monkey-patch _send to capture the JSON-RPC message
    captured = []

    def fake_send(message):
        captured.append(message)

    client._send = fake_send

    # Call request() with a list as params — the spec says only dicts are allowed
    try:
        client.request("test/method", [1, 2, 3])
    except Exception:
        pass  # Expected — no ELP server running

    if not captured:
        print("ERROR: _send was never called")
        sys.exit(1)

    sent_params = captured[0].get("params")
    is_dict = isinstance(sent_params, dict)

    if is_dict:
        print(
            f"NOT CONFIRMED — params converted to dict: {sent_params!r}"
        )
    else:
        print(
            f"CONFIRMED — actual params type: {type(sent_params).__name__}, "
            f"value: {sent_params!r} | expected: dict"
        )


if __name__ == "__main__":
    main()
