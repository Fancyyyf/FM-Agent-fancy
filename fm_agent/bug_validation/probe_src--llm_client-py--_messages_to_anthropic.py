import sys
import os

# Run from repo root
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
    """Reimplementation matching the specification exactly."""
    system_text_parts = []
    out = []
    for m in messages:
        role = m.get("role")
        content = m.get("content", "")
        if not isinstance(content, str):
            # Flatten content blocks: join text values with newlines
            content = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
        if role == "system":
            system_text_parts.append(content)
        elif role in ("user", "assistant"):
            out.append({"role": role, "content": content})
    
    # Build system_text per spec:
    # 0 system messages → ''
    # 1 system message → content verbatim (no strip)
    # 2+ system messages → concatenate with "\n\n", then strip
    if len(system_text_parts) == 0:
        system_text = ""
    elif len(system_text_parts) == 1:
        system_text = system_text_parts[0]
    else:
        system_text = "\n\n".join(system_text_parts).strip()
    
    return system_text, out


def run_test(name, messages):
    """Run one test case. Returns (passed, actual_str, expected_str)."""
    actual_sys, actual_out = _messages_to_anthropic(messages)
    expected_sys, expected_out = spec_correct_messages_to_anthropic(messages)
    
    sys_match = (actual_sys == expected_sys)
    out_match = (actual_out == expected_out)
    passed = sys_match and out_match
    
    if not passed:
        return False, repr(actual_sys), repr(expected_sys)
    return True, repr(actual_sys), repr(expected_sys)


# Test cases
all_passed = True
failures = []

# Test 1: Single system message (should work correctly - no strip)
msg1_actual, _ = _messages_to_anthropic([{"role": "system", "content": "  a  "}])
msg1_expected, _ = spec_correct_messages_to_anthropic([{"role": "system", "content": "  a  "}])
if msg1_actual != msg1_expected:
    all_passed = False
    failures.append(("single system", repr(msg1_actual), repr(msg1_expected)))

# Test 2: Two system messages (should work correctly - one strip at end)
msg2_actual, _ = _messages_to_anthropic([
    {"role": "system", "content": "  a  "},
    {"role": "system", "content": "  b  "},
])
msg2_expected, _ = spec_correct_messages_to_anthropic([
    {"role": "system", "content": "  a  "},
    {"role": "system", "content": "  b  "},
])
if msg2_actual != msg2_expected:
    all_passed = False
    failures.append(("two systems", repr(msg2_actual), repr(msg2_expected)))

# Test 3: THREE system messages — THIS IS WHERE THE BUG SHOULD MANIFEST
# The code strips intermediate content's trailing whitespace prematurely.
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

# Test 4: Trigger condition from the report
# [{'role':'system','content':'  a  '}, {'role':'system','content':'  b  '}]
# With only 2 messages, the code and spec should be equivalent —
# but let's verify exactly.
trigger_msgs = [
    {"role": "system", "content": "  a  "},
    {"role": "system", "content": "  b  "},
]
actual_trig, _ = _messages_to_anthropic(trigger_msgs)
expected_trig, _ = spec_correct_messages_to_anthropic(trigger_msgs)
if actual_trig != expected_trig:
    all_passed = False
    failures.append(("trigger condition (2 msgs)", repr(actual_trig), repr(expected_trig)))

# Test 5: Four system messages to be safe
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

# Test 6: No system messages
messages_none = [
    {"role": "user", "content": "hello"},
    {"role": "assistant", "content": "hi"},
]
actual_none_sys, actual_none_out = _messages_to_anthropic(messages_none)
expected_none_sys, expected_none_out = spec_correct_messages_to_anthropic(messages_none)
if actual_none_sys != expected_none_sys or actual_none_out != expected_none_out:
    all_passed = False
    failures.append(("no system", repr((actual_none_sys, actual_none_out)), repr((expected_none_sys, expected_none_out))))

# Test 7: Content blocks (lists of dicts) with multiple system messages
messages_blocks = [
    {"role": "system", "content": [{"text": "  first  "}]},
    {"role": "system", "content": [{"text": "second"}]},
    {"role": "system", "content": [{"text": "  third  "}]},
]
actual_blocks, _ = _messages_to_anthropic(messages_blocks)
expected_blocks, _ = spec_correct_messages_to_anthropic(messages_blocks)
if actual_blocks != expected_blocks:
    all_passed = False
    failures.append(("content blocks", repr(actual_blocks), repr(expected_blocks)))

# Report
if not all_passed:
    print("CONFIRMED — bug reproduced. Failures:")
    for name, act, exp in failures:
        print(f"  [{name}]")
        print(f"    actual:   {act}")
        print(f"    expected: {exp}")
else:
    print("NOT CONFIRMED — all test cases matched expected behavior")
