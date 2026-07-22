import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add snapshot root to path for imports
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot')

from src.languages.erlang import ElpClient

try:
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a real file with content so read_text doesn't fail
        real_file = Path(tmpdir) / "real.erl"
        real_file.write_text("-module(real).\n-export([hello/0]).\n\nhello() -> ok.\n")

        # Create a symlink pointing to the real file
        symlink = Path(tmpdir) / "link.erl"
        symlink.symlink_to(real_file)

        # Instantiate ElpClient — constructor does NOT spawn a subprocess
        # (only __enter__ does that, so this is safe)
        client = ElpClient(tmpdir)

        # Mock notify to capture the params argument
        captured_params = [None]

        def capture_notify(method, params):
            captured_params[0] = params

        with patch.object(client, 'notify', side_effect=capture_notify):
            client.open_document(str(symlink))

        # Extract the URI that was sent
        actual_uri = captured_params[0]['textDocument']['uri']

        # The spec says URI must represent the "path argument" (the symlink),
        # but resolve() follows symlinks to the target.
        expected_uri = symlink.as_uri()

        passed = actual_uri != expected_uri

        if passed:
            print(f'CONFIRMED — actual URI: {actual_uri!r} | expected URI: {expected_uri!r}')
        else:
            print(f'NOT CONFIRMED — actual URI matched expected: {actual_uri!r}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
