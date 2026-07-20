# Bug Report: record_llm_exchange

**Source file:** `src/trace_writer-py/record_llm_exchange.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When trace_dir is falsy, returns immediately with no side effects.
  - When trace_dir is a writable directory:
    - The content of each message in messages is durably stored as a separate file. Each stored message is classified by role: messages with role "system" are classified as system_prompt, role "user" as user_prompt, role "assistant" as assistant_output, and any other role as message.
    - If response is not None, its string value is durably stored as an additional file classified as assistant_output.
    - All stored files are recorded as child entries in the event dict. Each child entry contains a type field matching the classification, and a reference to the stored file content. Message-derived child entries additionally include the message's role.
    - Any existing "parsed" key is removed from event.metadata.
    - The event dict, with all child entries populated, is durably appended to the trace event log under trace_dir.

---

### Actual Behavior

If `trace_dir` is falsy (None or empty string), the function returns immediately; the mutable dict `event` and list `messages` are unchanged, and no side effects occur (no files created, no log appended). If `trace_dir` is a writable directory path, then: The `event` dict is modified as follows: a key `'metadata'` is set to a new dict obtained from the original `event.get('metadata', {})` (or an empty dict if absent) with the key `'parsed'` removed (if present); a key `'children'` is set to a list `children` constructed by iterating over `messages` with index `i` and mapping each message to a dict `{'type': item_type, 'role': role, 'content_ref': ref}` where `role = message.get('role', 'message')`, `item_type` is determined by `role` ('system''system_prompt', 'user''user_prompt', 'assistant''assistant_output', otherwise 'message'), `ref` is the result of calling `write_payload(trace_dir, event_id, filename, message.get('content', ''))` with `filename = f"message_{i:02d}_{role}.txt"`. If the parameter `response` is not None, an additional dict `{'type': 'assistant_output', 'content_ref': write_payload(trace_dir, event_id, 'response.txt', response)}` is appended to `children`. After constructing `children`, the function calls `record_trace_event(trace_dir, event)`, which atomically appends the modified `event` as a JSON line to the trace event log within `trace_dir`. Each `write_payload` call durably writes the given content to a file scoped under `event_id` inside `trace_dir` and returns a unique reference string. Formally, let `metadata0 = event.get('metadata', {})` at entry. Post-condition for the truthy case: `event == event0 {'metadata': metadata0 \{"parsed"}, 'children': children}` (with `event0` the initial event dict before modification) `i [0, len(messages)) .` the file for message `i` exists with content `messages[i].get('content', '')` `(response = None no response file) (response None response file exists with content ...`

---

## Code Evidence

Line 5: metadata = event.setdefault("metadata", {})

---

## Trigger Condition

The specification requires removal of an existing 'parsed' key from event.metadata but does not allow adding a 'metadata' key if one is absent. The code unconditionally sets a default empty metadata dict, which modifies event beyond the specified side effects, appending an extra key to the trace log.

---

## How to trigger the bug

Call `record_llm_exchange()` with a `trace_dir` that is a writable directory and an `event` dict that does **not** contain a `"metadata"` key. After the call, the `event` dict will have gained a `"metadata": {}` entry — a side effect not authorized by the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `trace_dir` | A writable temporary directory |
| `event_id` | `"test_001"` |
| `event` | `{"id": "evt_test_001", "type": "llm_exchange"}` (no "metadata" key) |
| `messages` | `[{"role": "user", "content": "hello"}]` |
| `response` | `None` |

### Expected (spec-correct) Output

The `event` dict should only have `"children"` added. The `"metadata"` key should NOT be added since it did not exist before the call (the spec only authorizes removal of `"parsed"` from an *existing* `event.metadata`).

### Actual (buggy) Output

The `event` dict gains both `"metadata": {}` and `"children"`. The `setdefault("metadata", {})` call on line 51 unconditionally inserts a `"metadata"` key even when one was absent.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, os.getcwd())
import tempfile, shutil
from src.trace_writer import record_llm_exchange

event = {"id": "evt_test_001", "type": "llm_exchange"}
before = dict(event)
tmpdir = tempfile.mkdtemp()

record_llm_exchange(
    trace_dir=tmpdir,
    event_id="test_001",
    event=event,
    messages=[{"role": "user", "content": "hello"}],
)

print("metadata" in before)  # False — no metadata key before
print("metadata" in event)   # True  — metadata key ADDED by setdefault()
print(event["metadata"])     # {}    — unauthorized side effect

shutil.rmtree(tmpdir)
# actual (buggy) output: event gains "metadata": {} key
# expected (correct) output: event should NOT gain a "metadata" key
```

---

## Probe Script

```python
import sys
import os

# Add repo root to sys.path so we can import 'src'
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

import tempfile
import shutil

try:
    from src.trace_writer import record_llm_exchange

    # Setup: an event dict WITHOUT a "metadata" key
    event = {"id": "evt_test_001", "type": "llm_exchange"}
    event_copy_before = dict(event)  # snapshot before call
    messages = [{"role": "user", "content": "hello"}]

    # Use a temp dir as trace_dir (truthy)
    tmpdir = tempfile.mkdtemp()

    record_llm_exchange(
        trace_dir=tmpdir,
        event_id="test_001",
        event=event,
        messages=messages,
        response=None,
    )

    # Check side effect: was "metadata" key ADDED to the event dict?
    had_metadata_before = "metadata" in event_copy_before
    has_metadata_after = "metadata" in event

    # The bug: setdefault("metadata", {}) adds "metadata" key even when absent.
    # The spec only permits removing "parsed" from event.metadata -- NOT adding
    # a metadata key where one didn't exist.
    if not had_metadata_before and has_metadata_after:
        print(f"CONFIRMED -- event had no 'metadata' key before call (keys: {list(event_copy_before.keys())}), "
              f"but after call has metadata={event['metadata']!r}. "
              f"The setdefault() on line 51 added an unauthorized key to the event dict.")
    else:
        print(f"NOT CONFIRMED -- event had_metadata_before={had_metadata_before}, "
              f"has_metadata_after={has_metadata_after}, "
              f"before keys: {list(event_copy_before.keys())}, "
              f"after keys: {list(event.keys())}")

    # Cleanup
    shutil.rmtree(tmpdir)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — event had no 'metadata' key before call (keys: ['id', 'type']), but after call has metadata={}. The setdefault() on line 51 added an unauthorized key to the event dict.
```
