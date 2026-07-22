# Bug Report: _messages_to_anthropic

**Source file:** `src/llm_client-py/_messages_to_anthropic.py`
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
      "system". When exactly one system-role message is present,
      system_text is its (possibly flattened) content string verbatim
      (with no whitespace stripping). When more than one system-role
      message is present, system_text is the result of concatenating
      their (possibly flattened) content strings in order, joining them
      with "\n\n", and then stripping leading and trailing whitespace
      from the entire concatenated result.
    - Messages whose role is neither "system", "user", nor "assistant" are
      excluded from both outputs.

---

### Actual Behavior

The function returns a tuple (system_text, out). Let processed_content(m) be: if m.get('content', '') is a string, use it; otherwise (content is a list), flatten it to a string by joining c.get('text', '') for each c in content that is a dict, separated by newlines. system_text is built from all messages m in input where m.get('role') == 'system': if there are no such messages, system_text is ''; if exactly one, system_text is processed_content(m) (without additional stripping); if more than one, system_text is the result of joining all processed_content of those messages in order with the separator '\\n\\n' and then stripping leading and trailing whitespace. out is a list of dictionaries {'role': m['role'], 'content': processed_content(m)}, preserving the relative order of those messages in the input, for each message where m.get('role') in {'user', 'assistant'}. The function has no side effects.

---

## Code Evidence

Line 13: system_text = (system_text + "\n\n" + content).strip() if system_text else content

---

## Trigger Condition

When there are multiple system messages, the code strips whitespace after each concatenation, causing interior whitespace to be lost. The specification requires concatenating all contents first with '\n\n' and then stripping only the final result. With the input [{'role':'system','content':'  a  '}, {'role':'system','content':'  b  '}], the code produces 'a  \n\n  b' while the spec requires 'a  \n\n  b  ', which differ.

---

## How to trigger the bug

The bug manifests when there are **3 or more** system messages where an intermediate message (not the first, not the last) has leading or trailing whitespace in its content. The code strips whitespace from each intermediate concatenation via `.strip()`, which removes trailing whitespace from intermediate messages before the next message is appended. The spec requires concatenating all raw contents first and stripping only the final result — so whitespace at the boundaries of intermediate messages is preserved.

With exactly 2 system messages, the code and spec produce the same result because there is only one concatenation-then-strip operation. The trigger condition in the report incorrectly claims a difference for 2 messages, but the real divergence occurs with 3+ messages.

### Inputs

| Parameter | Value |
|-----------|-------|
| messages[0] | `{"role": "system", "content": "a"}` |
| messages[1] | `{"role": "system", "content": "  b  "}` |
| messages[2] | `{"role": "system", "content": "c"}` |

### Expected (spec-correct) Output

`'a\n\n  b  \n\nc'`

(Trailing whitespace of "b" preserved because it is in the middle of the concatenated string; the spec only strips leading/trailing whitespace of the entire result.)

### Actual (buggy) Output

`'a\n\n  b\n\nc'`

(Trailing whitespace of "b" is stripped prematurely during the intermediate `.strip()` call at iteration 2.)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.llm_client import _messages_to_anthropic

messages = [
    {"role": "system", "content": "a"},
    {"role": "system", "content": "  b  "},
    {"role": "system", "content": "c"},
]

system_text, out = _messages_to_anthropic(messages)
# actual (buggy) output:   'a\n\n  b\n\nc'
# expected (correct) output: 'a\n\n  b  \n\nc'

print(repr(system_text))
# prints: 'a\\n\\n  b\\n\\nc'   (buggy — trailing whitespace of "b" lost)
# should be: 'a\\n\\n  b  \\n\\nc'   (correct — trailing whitespace of "b" preserved)
```

---

## Probe Script

```python
import sys
import os

repo_root = os.path.dirname(os.path.abspath(__file__))
while repo_root != '/' and not os.path.isfile(os.path.join(repo_root, 'main.py')):
    repo_root = os.path.dirname(repo_root)
os.chdir(repo_root)
sys.path.insert(0, repo_root)

import warnings
warnings.filterwarnings('ignore')

try:
    from src.llm_client import _messages_to_anthropic
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)


def spec_correct_messages_to_anthropic(messages):
    system_text_parts = []
    out = []
    for m in messages:
        role = m.get("role")
        content = m.get("content", "")
        if not isinstance(content, str):
            content = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
        if role == "system":
            system_text_parts.append(content)
        elif role in ("user", "assistant"):
            out.append({"role": role, "content": content})

    if len(system_text_parts) == 0:
        system_text = ""
    elif len(system_text_parts) == 1:
        system_text = system_text_parts[0]
    else:
        system_text = "\n\n".join(system_text_parts).strip()

    return system_text, out


all_passed = True
failures = []

messages_3 = [
    {"role": "system", "content": "a"},
    {"role": "system", "content": "  b  "},
    {"role": "system", "content": "c"},
]
actual_3, _ = _messages_to_anthropic(messages_3)
expected_3, _ = spec_correct_messages_to_anthropic(messages_3)
if actual_3 != expected_3:
    all_passed = False
    failures.append(("three systems (key test)", repr(actual_3), repr(expected_3)))

messages_4 = [
    {"role": "system", "content": "x  "},
    {"role": "system", "content": "  y"},
    {"role": "system", "content": "  z  "},
    {"role": "system", "content": "w"},
]
actual_4, _ = _messages_to_anthropic(messages_4)
expected_4, _ = spec_correct_messages_to_anthropic(messages_4)
if actual_4 != expected_4:
    all_passed = False
    failures.append(("four systems", repr(actual_4), repr(expected_4)))

if not all_passed:
    print("CONFIRMED — bug reproduced. Failures:")
    for name, act, exp in failures:
        print(f"  [{name}]")
        print(f"    actual:   {act}")
        print(f"    expected: {exp}")
else:
    print("NOT CONFIRMED — all test cases matched expected behavior")
```

### Probe Output

```
CONFIRMED — bug reproduced. Failures:
  [three systems (key test)]
    actual:   'a\n\n  b\n\nc'
    expected: 'a\n\n  b  \n\nc'
  [four systems]
    actual:   'x  \n\n  y\n\n  z\n\nw'
    expected: 'x  \n\n  y\n\n  z  \n\nw'
```
