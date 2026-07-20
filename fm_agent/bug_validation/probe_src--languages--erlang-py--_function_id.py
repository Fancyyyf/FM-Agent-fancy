"""Probe: Does _function_id retain leading '+'/'-' signs in arity from label?

Spec claims arity must be "stripped of any leading sign".
Code evidence (Line 318): uses arity directly without stripping.
Trigger: label = 'myfunc/+2' → result contains __+2 not __2.
"""
import sys
from src.languages.erlang import _function_id

label = "myfunc/+2"
uri = "file:///tmp/dummy/src/my_module.erl"

try:
    result = _function_id(uri, label)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# The spec requires arity stripped of leading sign.
# The buggy code returns __<raw_arity>, so we look for '+' or '-' in the arity portion.
parts = result.rsplit("__", 2)
if len(parts) != 3:
    print(f"ERROR: unexpected result format: {result!r} — expected exactly two '__' separators")
    sys.exit(1)

module, name, arity_str = parts
expected_arity = arity_str.lstrip("+-")

if arity_str.startswith("+") or arity_str.startswith("-"):
    print(f"CONFIRMED — arity has leading sign: {arity_str!r} (expected: {expected_arity!r}) | full result: {result!r}")
else:
    print(f"NOT CONFIRMED — arity has no leading sign: {arity_str!r} | full result: {result!r}")
