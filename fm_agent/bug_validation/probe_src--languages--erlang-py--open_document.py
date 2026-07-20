"""Probe script for bug src--languages--erlang-py--open_document.

Spec claim: open_document must raise an exception when the LSP communication
channel is not open.
Bug claim: The code calls self.notify() without checking channel state, so it
may return None instead of raising.
"""
import tempfile
from pathlib import Path
from src.languages.erlang import ElpClient


def main():
    # Create an ElpClient WITHOUT entering the context manager.
    # This leaves _proc = None, meaning the LSP channel is not open.
    client = ElpClient(proj_dir="/tmp")

    # Create a valid temp file so path resolution and file reading succeed.
    # Only the channel-not-open check (inside _send) should trigger.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".erl", delete=False) as f:
        f.write("-module(test).\n-export([hello/0]).\nhello() -> ok.\n")
        tmp_path = f.name

    try:
        # source=None forces file reading; the file exists so that step passes.
        # The buggy path is: path resolution OK, file read OK, then self.notify()
        # is called while _proc is None. According to the spec, this MUST raise.
        result = client.open_document(tmp_path, source=None)
        # If we get here, the function returned normally (returned None implicitly).
        # Per the spec this is a violation — an exception should have been raised.
        print(
            "CONFIRMED "
            f"— open_document with no channel returned {result!r} instead of raising"
        )
    except Exception as exc:
        # An exception was raised, which satisfies the specification.
        # The function correctly raised when the channel was not open.
        print(
            f"NOT CONFIRMED "
            f"— open_document with no channel correctly raised {type(exc).__name__}: {exc}"
        )
    finally:
        # Clean up the temp file.
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    main()
