"""Probe: Does _module_from_uri return stems containing '__'?

Spec claims the result "contains no instances of the double-underscore sequence ('__')".
Code evidence (Line 306): return PurePosixPath(path.replace("\\", "/")).stem
Trigger: uri = "http://example.com/__init__.py" → PurePosixPath.stem returns "__init__" which contains "__".
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.languages.erlang import _module_from_uri
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

uri = "http://example.com/__init__.py"

try:
    actual = _module_from_uri(uri)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Spec requires no "__" in result. The buggy code returns "__init__" which contains "__".
contains_double_underscore = "__" in actual

if contains_double_underscore:
    print(f"CONFIRMED — result contains double-underscore: {actual!r} | spec requires no '__' in result")
else:
    print(f"NOT CONFIRMED — result has no double-underscore: {actual!r}")
