"""Probe script for bug: _fingerprint_digest non-deterministic for equal tuples with dicts."""
import sys
import os

# Add src/ to sys.path so we can import the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
sys.path.insert(0, "src")

try:
    from languages.erlang import _fingerprint_digest
except ImportError:
    sys.path.insert(0, os.path.abspath("src"))
    from languages.erlang import _fingerprint_digest

# Two tuples that are equal in Python (t1 == t2)
# but contain dicts with different key insertion orders
t1 = ({"a": 1, "b": 2},)
t2 = ({"b": 2, "a": 1},)

# Sanity check: they ARE equal in Python
assert t1 == t2, f"Pre-condition violated: t1 != t2"

d1 = _fingerprint_digest(t1)
d2 = _fingerprint_digest(t2)

# Bug confirmation: equal tuples produce DIFFERENT digests
bug_exists = (d1 != d2)

if bug_exists:
    print(f"CONFIRMED — actual: d1={d1!r} | d2={d2!r} | t1 == t2 is {t1 == t2}")
else:
    print(f"NOT CONFIRMED — actual matched: d1={d1!r} | d2={d2!r}")
