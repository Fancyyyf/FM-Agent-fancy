# Bug Report: _messages_to_anthropic

**Source file:** `src/llm_client.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a pair (system_text, anthropic_messages) where:
    - anthropic_messages is a list of dicts, each with exactly the keys
      "role" and "content", containing every input message whose role is
      "user" or "assistant", in their original relative order.
    - For an input message whose "content" value is a string, it passes
      through unchanged. When "content" is a list of dicts (content blocks),
      it is replaced with a single string formed by joining the "text" value
      of each dict in the list with newline separators. A dict in the list
      without a "text" key contributes an empty string at that position.
    - system_text is the empty string when no input message has role
      "system". When one or more system-role messages are present,
      system_text is the concatenation of their (possibly flattened) content
      strings, joined by "\n\n", with leading and trailing whitespace
      removed.
    - Messages whose role is neither "system", "user", nor "assistant" are
      excluded from both outputs.

---

### Actual Behavior

The function either raises a TypeError if any message's 'content' is neither a string nor an iterable, or returns normally with a tuple (system_text, out). When returning normally, system_text is a string composed of the processed 'content' from all messages where role is 'system', concatenated with '\n\n' separator when multiple, with stripping applied only after concatenations (i.e., if there is exactly one system message, its content is used as is; otherwise the concatenated result is stripped). For each system message, if its content is a string it is used directly; if it is a list (or iterable) of dictionaries, it is flattened into a newline-separated string of their 'text' values, ignoring non-dict items. Similarly, out is a list of dictionaries {'role': role, 'content': processed_content} for every message where role is 'user' or 'assistant', with the same content transformation. Messages with other roles or without a 'role' key are ignored. Formally: let processed(m) = m['content'] if it is a string; else '\n'.join(c.get('text', '') for c in m['content'] if isinstance(c, dict)) provided m['content'] is iterable. TypeError occurs if any m['content'] is not a string and not iterable. Otherwise, define S = [processed(m) for m in messages if m.get('role') == 'system']. Then system_text = S[0] if |S| = 1; else '\n\n'.join(S).strip() if |S| > 1; else ''. And out = [{'role': m['role'], 'content': processed(m)} for m in messages if m.get('role') in ('user', 'assistant')].

---

## Code Evidence

Line 13: system_text = (system_text + "\n\n" + content).strip() if system_text else content

---

## Trigger Condition

The specification requires leading/trailing whitespace removal for system_text even when there is exactly one system message. The code does not strip the content when there is only one system message (line 13 else branch), so an input with a single system message containing surrounding whitespace yields a wrong system_text.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| messages | `[{"role": "system", "content": "  hello world  "}]` |

### Expected (spec-correct) Output

`("hello world", [])`

### Actual (buggy) Output

`("  hello world  ", [])`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.llm_client import _messages_to_anthropic

messages = [{"role": "system", "content": "  hello world  "}]
system_text, an_msgs = _messages_to_anthropic(messages)

# actual (buggy) output: system_text = "  hello world  "
# expected (correct) output: system_text = "hello world"
print(repr(system_text))
# Outputs: '  hello world  ' (whitespace NOT stripped)
```

---

## Probe Script

```python
import sys

try:
    from src.llm_client import _messages_to_anthropic

    # Single system message with surrounding whitespace — the code path on line 93
    # takes the "else content" branch (no strip), while the spec requires stripping.
    messages = [{"role": "system", "content": "  hello world  "}]
    system_text, an_msgs = _messages_to_anthropic(messages)

    # Spec: system_text must have leading/trailing whitespace removed.
    expected = "hello world"
    actual = system_text

    # Bug confirmed if actual does NOT match expected (whitespace was not stripped).
    passed = actual != expected
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: '  hello world  ' | expected: 'hello world'
```
