"""Probe for bug: ElpClient._send does not raise RuntimeError when stdin is unavailable."""

import sys
import threading
from unittest.mock import MagicMock

# Package entry-point import
sys.path.insert(0, '.')
from src.languages.erlang import ElpClient


def main():
    try:
        client = ElpClient('/tmp')

        # Simulate: self._proc is not None and self._proc.stdin is not None,
        # but stdin is closed/unavailable (e.g., pipe already closed).
        mock_proc = MagicMock()
        mock_stdin = MagicMock()
        mock_stdin.closed = True
        mock_stdin.write.side_effect = ValueError('write to closed file')
        mock_stdin.flush.side_effect = ValueError('flush on closed file')
        mock_proc.stdin = mock_stdin

        client._proc = mock_proc
        client._write_lock = threading.Lock()

        # Call a public method that internally uses _send
        client.notify('test/method', {'key': 'val'})

        # Spec requires RuntimeError; code reached here → bug NOT confirmed
        print('NOT CONFIRMED — no exception raised, but RuntimeError expected per spec')
    except RuntimeError:
        # RuntimeError IS raised → code matches spec → bug NOT confirmed
        print('NOT CONFIRMED — RuntimeError raised, which matches the spec')
    except Exception as exc:
        actual_type = type(exc).__name__
        expected = 'RuntimeError'

        if actual_type != expected:
            # Wrong exception type raised → bug CONFIRMED
            print(
                f'CONFIRMED — code raised {actual_type}("{exc}") '
                f'but spec requires {expected} when stdin is unavailable. '
                f'_proc.stdin is non-None (mock: {mock_stdin!r}) '
                f'yet stdin is closed/unavailable.'
            )
        else:
            print('NOT CONFIRMED — RuntimeError raised as expected')

if __name__ == '__main__':
    main()
