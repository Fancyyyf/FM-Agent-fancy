"""Probe script for bug src--languages--erlang-py--_escape_component.

The bug: _escape_component does not prevent double-underscore ("__") in output
when an underscore in the input is followed by a character that escapes to '_xx'.

Trigger condition: input "_:" yields "__3a" which violates the spec.
"""
import sys

try:
    from src.languages.erlang import _escape_component
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

input_value = "_:"
try:
    actual = _escape_component(input_value)
except Exception as e:
    print(f'ERROR: call failed — {e}')
    sys.exit(1)

# The spec requires: "The returned string contains no occurrence of the substring '__'"
# The buggy code produces '__3a' which violates this.
has_double_underscore = "__" in actual
passed = has_double_underscore  # True → bug confirmed

if passed:
    print(f'CONFIRMED — input {input_value!r} produced {actual!r} which contains "__"')
else:
    print(f'NOT CONFIRMED — input {input_value!r} produced {actual!r} without "__"')
