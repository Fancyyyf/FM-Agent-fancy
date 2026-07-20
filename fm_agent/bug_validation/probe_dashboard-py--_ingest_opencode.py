"""Probe script v3 for bug dashboard-py--_ingest_opencode.

Tests variant: response record with NO status field at all, but valid usage dict.
If the FM-Agent claim were correct, the code would ignore this too.
"""

import sys
import tempfile
from pathlib import Path

try:
    import dashboard
except ImportError:
    print('ERROR: cannot import dashboard module')
    sys.exit(1)

State = dashboard.State

tmpdir = tempfile.mkdtemp(prefix='probe_opencode_v3_')
(trace_dir := Path(tmpdir) / 'trace').mkdir()
(trace_dir / 'opencode').mkdir()
(Path(tmpdir) / 'bug_validation').mkdir()

state = State(tmpdir)
state.opencode_calls = 0
state.opencode_token_totals = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
state.opencode_cost = 0.0
state.cache_window.clear()
state._opencode_requests.clear()

state._ingest_opencode({
    "_kind": "request",
    "_id": "call-003",
    "_ts": "2024-06-01T12:00:00Z",
    "_trace_file": "trace3.jsonl",
    "model": "claude-sonnet-4-20250514",
    "_url": "https://api.anthropic.com/v1/messages",
    "_purpose": "no-status-test",
}, trace_file="trace3.jsonl")

# Response with NO status field whatsoever, but valid usage
response_rec = {
    "_kind": "response",
    "_id": "call-003",
    "_ts": "2024-06-01T12:00:05Z",
    "_trace_file": "trace3.jsonl",
    "model": "claude-sonnet-4-20250514",
    "usage": {
        "input_tokens": 75,
        "output_tokens": 25,
        "cache_read_input_tokens": 10,
        "cache_creation_input_tokens": 5,
    },
}

state._ingest_opencode(response_rec, trace_file="trace3.jsonl")

actual_calls = state.opencode_calls
actual_input = state.opencode_token_totals.get("input", 0)
actual_output = state.opencode_token_totals.get("output", 0)
actual_cr = state.opencode_token_totals.get("cache_read", 0)
actual_cw = state.opencode_token_totals.get("cache_write", 0)
actual_cache_len = len(state.cache_window)

expected_calls = 1
expected_input = 75
expected_output = 25
expected_cr = 10
expected_cw = 5
expected_cache_len = 1  # total_in = 75+10+5 = 90 > 0

all_match = (
    actual_calls == expected_calls
    and actual_input == expected_input
    and actual_output == expected_output
    and actual_cr == expected_cr
    and actual_cw == expected_cw
    and actual_cache_len == expected_cache_len
)

if not all_match:
    print(
        f"CONFIRMED — actual differs: calls={actual_calls}(exp={expected_calls}), "
        f"input={actual_input}(exp={expected_input}), "
        f"output={actual_output}(exp={expected_output}), "
        f"cr={actual_cr}(exp={expected_cr}), cw={actual_cw}(exp={expected_cw}), "
        f"cache_len={actual_cache_len}(exp={expected_cache_len})"
    )
else:
    print(
        f"NOT CONFIRMED — actual matched expected: calls={actual_calls}, "
        f"input={actual_input}, output={actual_output}, "
        f"cr={actual_cr}, cw={actual_cw}, cache_len={actual_cache_len}"
    )

import shutil
shutil.rmtree(tmpdir, ignore_errors=True)
