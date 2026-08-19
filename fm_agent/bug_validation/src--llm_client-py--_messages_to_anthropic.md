# Bug Report: _messages_to_anthropic

**Source file:** `src/llm_client.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a tuple (system_text, msgs) translating the conversation into the Anthropic messages API shape. system_text is the string formed from the textual content of every system-role message taken in original order, with consecutive system messages separated by a blank line, and is the empty string when no system-role message is present. msgs is a list of {role, content} entries preserving, in original order, exactly the messages whose role is one of the non-system conversational roles accepted by the Anthropic messages API, each entry's content being a string. Messages whose role is neither system nor an accepted conversational role contribute nothing to either output. When a message's content is a list of blocks, the output content string is the texts of the dict-typed block elements joined in original order by newline characters, with a block lacking a text field contributing an empty string; string content passes through unchanged. The input list and its message dicts are never mutated. The function raises no exception under the stated pre-condition.

---

### Actual Behavior

The function returns a 2-tuple (system_text, out) where:

1. system_text (str): The concatenation of the processed content of every message in `messages` whose 'role' field equals 'system', joined by '\n\n', with leading/trailing whitespace stripped. If no system-role messages exist, system_text == ''. The joining logic is: the first system message's content is used as-is; each subsequent system message appends '\n\n' + content, and the final result is .strip()-ed.

2. out (list[dict]): An ordered list containing one dict {'role': r, 'content': c} for each message in `messages` whose 'role' field is 'user' or 'assistant', preserving the original order. Messages with any other role value (including None or unrecognized strings) are excluded from both system_text and out.

3. Content normalization: For each message, if the 'content' field is absent it defaults to ''. If 'content' is not a str (i.e., it is a list of block dicts per the pre-condition), it is flattened to a single string by joining the 'text' field (defaulting to '') of each element that is a dict, separated by '\n'; non-dict elements in the list are discarded. If 'content' is already a str, it is used unchanged.

4. The input list `messages` and its contained dicts are not mutated.

5. No exceptions are raised under the stated pre-condition (all 'role' values are strings, 'content' is str or list of dicts).

Formally:
   i  [0, len(messages)): let m_i = messages[i], r_i = m_i.get('role'), c_i = normalize(m_i.get('content', ''))
  where normalize(x) = x if isinstance(x, str) else '\n'.join(d.get('text','') for d in x if isinstance(d, dict))

  system_text = strip(join('\n\n', [c_i | r_i == 'system'])) if any r_i == 'system' else ''
  out = [{'role': r_i, 'content': c_i} | r_i  {'user','assistant'}] (order-preserving)
  return (system_text, out)

---

## Code Evidence

Line 13: system_text = (system_text + "\n\n" + content).strip() if system_text else content

---

## Trigger Condition

The specification requires that consecutive system messages be separated by a blank line (i.e., joined with '\n\n'), regardless of their content. The code uses the truthiness of `system_text` to decide whether to append or start fresh. When the first system message has empty-string content, `system_text` remains "" (falsy), so the second system message is treated as if it were the first, discarding the required '\n\n' separator. For the input [{"role":"system","content":""},{"role":"system","content":"hello"}], the code returns system_text="hello", but the specification requires system_text="\n\nhello" (the join of ["", "hello"] with '\n\n').

---

## How to trigger the bug

The conversation passed to `_messages_to_anthropic` contains two consecutive
system-role messages where the first has empty-string content and the second
has content `"hello"`. The buggy code (line 92 of `src/llm_client.py`, the
line quoted in the code evidence) keys the append-vs-start-fresh decision on
the truthiness of the accumulated `system_text`:

```python
system_text = (system_text + "\n\n" + content).strip() if system_text else content
```

After the first (empty) system message, `system_text` is still `""` (falsy),
so the second system message is treated as if it were the first and is
assigned directly, discarding the blank-line (`'\n\n'`) separator the
specification requires between consecutive system messages regardless of
their content. The spec-correct value is `'\n\n'.join(["", "hello"])`,
i.e. `"\n\nhello"`, while the code returns `"hello"`. The probe exercises
the smallest relevant unit through the package entry point `from src import
llm_client` (no FM-Agent workflow, no network, no file I/O).

### Inputs

| Parameter | Value |
|-----------|-------|
| `messages` | `[{"role": "system", "content": ""}, {"role": "system", "content": "hello"}]` |

### Expected (spec-correct) Output

`('\n\nhello', [])`

### Actual (buggy) Output

`('hello', [])`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
os.environ.setdefault("LLM_API_KEY", "probe-dummy-key")  # satisfies module-level OpenAI client construction; no request is made
from src import llm_client

system_text, msgs = llm_client._messages_to_anthropic(
    [{"role": "system", "content": ""}, {"role": "system", "content": "hello"}]
)
print(repr((system_text, msgs)))
# actual (buggy) output: ('hello', [])
# expected (correct) output: ('\n\nhello', [])
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe for bug src--llm_client-py--_messages_to_anthropic.

Spec claim (_messages_to_anthropic, src/llm_client.py): returns a tuple
(system_text, msgs) where system_text is formed from the textual content of
every system-role message taken in original order, with consecutive system
messages separated by a blank line ('\\n\\n'); msgs preserves the non-system
conversational messages.

Suspected actual behavior: the append-vs-start branch keys off the truthiness
of the accumulated system_text (line 13 of the extracted function, line 92 of
src/llm_client.py):

    system_text = (system_text + "\\n\\n" + content).strip() if system_text else content

When the first system message has empty-string content, system_text remains
"" (falsy), so the second system message is treated as if it were the first
and the required '\\n\\n' separator is discarded.

Trigger input (from the reported trigger condition):
    [{"role": "system", "content": ""}, {"role": "system", "content": "hello"}]
Buggy output:     system_text == "hello"
Spec-correct:     system_text == "\\n\\nhello"   ('\\n\\n'.join(["", "hello"]))

Entry-point note (FM-Agent self-validation guard): every caller of
_messages_to_anthropic (_anthropic_create, _retry_create, _llm_json_call, and
the spec-generation/spec-check helpers in src/prompts.py) is itself private
and ultimately performs live LLM HTTP requests as part of an FM-Agent
workflow. No public API reaches this helper without starting an FM-Agent
workflow, which this probe must not do. Per the guard, the smallest relevant
unit is tested directly, loading the module exclusively through the package
entry point `from src import llm_client` (no direct file loading, no
run_pipeline/main.py/OpenCode/subprocess).

The probe performs no network calls and no file I/O beyond loading project
modules; everything runs in memory, so no temporary workspace is required. A
dummy LLM_API_KEY is supplied via process env (config precedence: env > .env
> toml) only so the module-level OpenAI client construction succeeds; it is
never used for any request.
"""

import os
import sys

# Repo root is two directories above fm_agent/bug_validation/probe_*.py
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)


def main():
    try:
        # Satisfy module-level OpenAI(...) construction in src/llm_client.py
        # without touching any real credentials (setdefault keeps a real key
        # if one happens to be configured).
        os.environ.setdefault("LLM_API_KEY", "probe-dummy-key")

        from src import llm_client  # load via the package entry point

        # Trigger input from the reported condition: a leading system message
        # with empty-string content followed by a non-empty system message.
        messages = [
            {"role": "system", "content": ""},
            {"role": "system", "content": "hello"},
        ]
        snapshot = [
            {"role": "system", "content": ""},
            {"role": "system", "content": "hello"},
        ]

        actual_system, actual_msgs = llm_client._messages_to_anthropic(messages)

        # Spec-correct expectation: every system-role message's content taken
        # in original order and separated by a blank line; there are no
        # non-system conversational messages in the input.
        expected_system = "\n\nhello"
        expected_msgs: list = []

        # The spec also requires the input list and its dicts never mutate.
        if messages != snapshot:
            print("ERROR: _messages_to_anthropic mutated its input messages")
            return 1
    except Exception as exc:
        print(f"ERROR: probe raised: {type(exc).__name__}: {exc}")
        return 1

    reproduced = (actual_system != expected_system) or (actual_msgs != expected_msgs)
    if reproduced:
        print(
            f"CONFIRMED — actual: ({actual_system!r}, {actual_msgs!r}) | "
            f"expected: ({expected_system!r}, {expected_msgs!r})"
        )
    else:
        print(
            f"NOT CONFIRMED — actual matched expected: "
            f"({actual_system!r}, {actual_msgs!r})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### Probe Output

```
CONFIRMED — actual: ('hello', []) | expected: ('\n\nhello', [])
```
