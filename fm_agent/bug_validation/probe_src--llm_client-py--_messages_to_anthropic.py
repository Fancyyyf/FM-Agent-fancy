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
