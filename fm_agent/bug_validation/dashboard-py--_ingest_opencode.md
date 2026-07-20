# Bug Report: _ingest_opencode

**Source file:** `dashboard.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Records with "_kind" == "request" AND a non-None "_id": the
    request metadata (timestamp, model, URL, purpose) is stored
    internally keyed by (trace_file, call_id).  No user-visible
    aggregated metric changes.
  - Records with "_kind" == "error": an error entry is appended to
    the LLM-status history.  No token or cost totals change.
  - Records with "_kind" != "response": no side effects beyond the
    request and error handling described above.
  - Records with "_kind" == "response":
      * If the HTTP status code (from any of "_status", "status",
        "status_code") is present and not 200, an error entry is
        appended to the LLM-status history.  No token or cost totals
        change.
      * If "usage" is not a dict (missing or non-dict value), a
        success entry is appended to the LLM-status history.  No
        token or cost totals change.
      * If "usage" is a dict but contains no token counts (i.e.,
        both input and output tokens resolve to zero), a success
        entry is appended to the LLM-status history.  No token or
        cost totals change.
      * Otherwise (usage is a dict with non-zero token counts):
        - A success entry is appended to the LLM-status history.
        - self.opencode_calls is incremented by 1.
        - self.opencode_token_totals["input"],
          self.opencode_token_totals["output"],
          self.opencode_token_totals["cache_read"], and
          self.opencode_token_totals["cache_write"] are increased
          by the corresponding token counts resolved from the usage
          dict, supporting both Anthropic-native and OpenAI-compat
          shapes (with DeepSeek cache-hit/miss splitting for the
          OpenAI compat path).
        - self.opencode_cost is increased by the cost computed from
          the model and resolved usage.
        - If total input tokens (input + cache_read + cache_write)
          for this response are positive, the pair
          (cache_read_tokens, total_input_tokens) is appended to
          self.cache_window.
  - Missing optional fields (keys absent or None) do not cause
    errors; the corresponding metric updates or status entries are
    simply skipped.
  - The strip-started normalization is applied transparently so
    that records from streaming-delta key formats and plain-key
    formats are handled identically.

---

### Actual Behavior

After completing execution of _ingest_opencode, the state of self is transformed as follows:

Case 1: rec._kind is "request" and rec._id is not None.
    - self._opencode_requests is updated: for fresh_key = (trace_key, call_id) where trace_key = rec.get("_trace_file") or trace_file, and call_id = rec["_id"], the entry self._opencode_requests[fresh_key] is set to a dict with keys "ts" (datetime or None, parsed from rec._ts), "model" (value of rec.model, or None), "url" (value of rec._url, or None), and "purpose" (value of rec._purpose, or None).
    - All other attributes of self (opencode_calls, opencode_token_totals, opencode_cost, cache_window, LLM-status history, and _opencode_requests entries for other keys) remain unchanged.

Case 2: rec._kind is "error".
    - A new error record is appended to the LLM-status history (the bounded internal list). The record contains the keys:
        ts: _parse_iso(rec.get("_ts")) if truthy, otherwise req.get("ts") (where req = self._opencode_requests.get((trace_key, call_id), {})).
        source: "opencode".
        label: req.get("purpose") if truthy, else rec.get("_purpose") or rec.get("_url") or "opencode".
        status: "error".
        model: rec.get("model") if truthy, else req.get("model").
        code: _trace_value(rec, "_status", "status", "status_code") if truthy, else "ERR".
        detail: _trace_value(rec, "_error", "error", "message") (could be None).
    - self._opencode_requests is not modified.
    - All other attributes remain unchanged.

Case 3: rec._kind is "response" and the extracted status_code (via _trace_value(rec, "_status", "status", "status_code")) is truthy and not equal to the string "200".
    - An error record is appended to the LLM-status history with:
        ts: _parse_iso(rec.get("_ts")) if truthy, else req.get("ts") (req as above).
        source: "opencode".
        label: req.get("purpose") if truthy, else rec.get("_purpose") or rec.get("_url") or "opencode".
        status: "error".
        model: rec.get("model") if truthy, else req.get("model").
        code: the status_code value (as string or original type).
        detail: None (not provided).
    - self._opencode_requests is not modified.
    - All other attributes remain unchanged.

Case 4: All other scenarios (rec._kind is not "request", not "error", not "response"; or rec._kind is "request" but rec._id is None; or rec._kind is "response" with no status_code or status_code == "200"; etc.).
    - self is completely unchanged: all attributes have their original values.

In all cases, no exceptions are raised by the helpers under normal operation (they handle missing/falsy inputs gracefully, returning None where appropriate). If an unexpected exception occurs, self may be partially updated up to the point of failure and the exception propagates.

Formal logic (using S for self, S0 for initial state, _oreqs for _opencode_requests, _llm_hist for the LLM-status history list, and letting rec = _strip_star(rec)):
((rec._kind = "request"  rec._id  None) 
   ( fresh_key = (rec._trace_file or trace_file, rec._id).
    S._oreqs = S0._oreqs  {fresh_key  {"ts": _parse_iso(rec._ts),
                                       "model": rec.model,
                                       "url": rec._url,
                                       "purpose": rec._purpose}}) 
    S.opencode_calls = S0.opencode_calls 
    S.opencode_token_totals = S0.opencode_token_totals 
    S.opencode_cost = S0.opencode_cost 
    S.cache_window = S0.cache_window 
    S._llm_hist = S0._llm_hist))
 ((rec._kind = "error") 
   (S._llm_hist = S0._llm_hist  [error_record] 
    S._oreqs = S0._oreqs 
    S.opencode_calls = S0.opencode_calls 
    S.opencode_token_totals = S0.opencode_token_totals 
    S.opencode_cost = S0.opencode_cost 
    S.cache_window = S0.cache_window))
 ((rec._kind = "response"  (let sc = _trace_value(rec, "_status", "status", "status_code") in sc truthy  str(sc)  "200")) 
   (S._llm_hist = S0._llm_hist  [resp_error_record] 
    S._oreqs = S0._oreqs 
    ... same other fields unchanged ...))
 (otherwise  S = S0)

where  denotes dictionary update (fresh key added or old value replaced with new dict), and  denotes list append with possible bounded eviction as per _push_llm_status. The exact records are specified in the natural language cases above.

---

## Code Evidence

Lines 29-40: The code only handles non-response records and non-200 responses, and completely ignores successful responses (status 200 or missing status) that should update opencode_calls, opencode_token_totals, opencode_cost, and cache_window.

---

## Trigger Condition

For a response with status 200 and a 'usage' dict containing non-zero token counts, the specification requires incrementing self.opencode_calls, updating token totals and cost, and appending to cache_window. However, condition A (Case 4) states that self remains unchanged for all inputs not covered by Cases 1-3. Therefore, a successful response with usage causes no state change, violating the specification.

---

## How to trigger the bug

The static analysis (FM-Agent) claimed that `_ingest_opencode` ignores successful responses (status 200 or missing status). However, **3 independent probe scripts** were unable to reproduce this bug. In all three variants, the code correctly updated `opencode_calls`, token totals, cost, and `cache_window`.

**Root cause of false positive:** The FM-Agent reasoning incorrectly deduced a "Case 4" post-condition stating "self remains unchanged for all inputs not covered by Cases 1-3." In the actual code, after the non-200 status check on line 398 (`if status_code and str(status_code) != "200"`), execution falls *through* to lines 409-469 which handle status-200 and missing-status responses with full metric updates. The reasoning engine mistakenly concluded that all response-handling paths end with an early `return`, when only the non-200 path returns early.

### Inputs

| Parameter | Value |
|-----------|-------|
| `rec._kind` | `"response"` |
| `rec._id` | `"call-003"` |
| `rec._ts` | `"2024-06-01T12:00:05Z"` |
| `rec._trace_file` | `"trace3.jsonl"` |
| `rec.model` | `"claude-sonnet-4-20250514"` |
| `rec.usage` | `{"input_tokens": 75, "output_tokens": 25, "cache_read_input_tokens": 10, "cache_creation_input_tokens": 5}` |
| Preceding request | Same `_id`, `_trace_file` with matching `_purpose` |

### Expected (spec-correct) Output

`opencode_calls = 1`, `opencode_token_totals["input"] = 75`, `opencode_token_totals["output"] = 25`, `opencode_token_totals["cache_read"] = 10`, `opencode_token_totals["cache_write"] = 5`, `cache_window = [(10, 90)]`, LLM status history contains one `"success"` entry.

### Actual (buggy) Output

Same as expected — the code behaves correctly, matching the specification.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from pathlib import Path
import tempfile
import dashboard

tmpdir = tempfile.mkdtemp()
(Path(tmpdir) / "trace").mkdir()
(Path(tmpdir) / "trace" / "opencode").mkdir()
state = dashboard.State(tmpdir)
state.opencode_calls = 0
state.opencode_token_totals = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
state.opencode_cost = 0.0
state.cache_window.clear()

# Preceding request
state._ingest_opencode({
    "_kind": "request", "_id": "call-003",
    "_ts": "2024-06-01T12:00:00Z", "_trace_file": "trace3.jsonl",
    "model": "claude-sonnet-4-20250514", "_purpose": "test",
}, trace_file="trace3.jsonl")

# Response with status 200 and valid usage
state._ingest_opencode({
    "_kind": "response", "_id": "call-003",
    "_ts": "2024-06-01T12:00:05Z", "_trace_file": "trace3.jsonl",
    "model": "claude-sonnet-4-20250514",
    "status": 200,
    "usage": {"input_tokens": 150, "output_tokens": 80},
}, trace_file="trace3.jsonl")

print(state.opencode_calls)          # actual (correct) output: 1
print(state.opencode_token_totals)   # actual (correct) output: {'input': 150, 'output': 80, ...}
# expected (correct) output: 1, {'input': 150, 'output': 80, ...}
```

---

## Probe Script

```python
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
```

### Probe Output

```
NOT CONFIRMED — actual matched expected: calls=1, input=75, output=25, cr=10, cw=5, cache_len=1
```
