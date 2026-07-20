import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')))

try:
    from src.generate_topdown_layers import _detect_lang_from_ext
    from src.extract import EXT_TO_LANG

    # Check EXT_TO_LANG key format
    dotted_keys = [k for k in EXT_TO_LANG.keys() if k.startswith('.')]
    dotless_keys = [k for k in EXT_TO_LANG.keys() if not k.startswith('.')]

    print(f"EXT_TO_LANG total keys: {len(EXT_TO_LANG)}")
    print(f"EXT_TO_LANG dotted keys (e.g. '.py'): {dotted_keys}")
    print(f"EXT_TO_LANG dotless keys (e.g. 'py'): {dotless_keys}")

    # Test 1: .py file should return "python"
    actual1 = _detect_lang_from_ext("test.py")
    expected1 = "python"
    print(f"\nTest 1: _detect_lang_from_ext('test.py')")
    print(f"  Actual:   {actual1!r}")
    print(f"  Expected: {expected1!r}")

    # Test 2: .cpp file should return "cpp"
    actual2 = _detect_lang_from_ext("foo.cpp")
    expected2 = "cpp"
    print(f"\nTest 2: _detect_lang_from_ext('foo.cpp')")
    print(f"  Actual:   {actual2!r}")
    print(f"  Expected: {expected2!r}")

    # Test 3: unknown extension should return None
    actual3 = _detect_lang_from_ext("foo.xyz")
    expected3 = None
    print(f"\nTest 3: _detect_lang_from_ext('foo.xyz')")
    print(f"  Actual:   {actual3!r}")
    print(f"  Expected: {expected3!r}")

    # Test 4: no extension should return None (empty string lookup)
    actual4 = _detect_lang_from_ext("foo")
    expected4 = None
    print(f"\nTest 4: _detect_lang_from_ext('foo')")
    print(f"  Actual:   {actual4!r}")
    print(f"  Expected: {expected4!r}")

    # Determine overall verdict
    all_passed = (
        actual1 == expected1 and
        actual2 == expected2 and
        actual3 == expected3 and
        actual4 == expected4
    )

    if all_passed:
        print("\nNOT CONFIRMED — function behaves correctly with current EXT_TO_LANG (dotless keys match dot-stripped extension lookup)")
    else:
        print(f"\nCONFIRMED — mismatch detected: function returns unexpected values")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
