import sys
import os

# Add repo root to path: probe is at fm_agent/bug_validation/probe_*.py (3 levels down)
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.generate_batch_prompts import detect_lang_and_comment

    # Trigger condition: file_rel='Makefile' (no dot → no extension),
    # with ext_to_lang mapping the empty string '' to a language.
    # Per the spec, when there is no extension, lang must be 'unknown'
    # regardless of whether '' is a key in ext_to_lang.
    # The buggy code calls ext_to_lang.get('', '' if '' else 'unknown')
    # which = ext_to_lang.get('', 'unknown'), returning 'makefile_lang' instead of 'unknown'.
    actual = detect_lang_and_comment("Makefile", {"": "makefile_lang"})
    expected = ("unknown", "//")

    passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
