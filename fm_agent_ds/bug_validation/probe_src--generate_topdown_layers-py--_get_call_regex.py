import sys
sys.path.insert(0, ".")

try:
    from src.generate_topdown_layers import _get_call_regex

    test_cases = {
        # (lang_key, test_input, expected_name) — spec says nested brackets should be tolerated
        "cpp":    [("foo<A<B>>(x)", "foo", "cpp nested template args")],
        "rust":   [("bar::<Vec<u8>>(x)", "bar", "rust nested turbofish")],
        "go":     [("fn[map[string]int](x)", "fn", "go nested type params")],
    }

    mismatches = []
    matches_ok = []

    for lang_key, cases in test_cases.items():
        regex = _get_call_regex(lang_key)
        for text, expected_name, desc in cases:
            m = regex.search(text)
            actual = m.group(1) if m else None
            if actual != expected_name:
                mismatches.append((lang_key, text, expected_name, actual, desc))
            else:
                matches_ok.append((lang_key, text, expected_name, desc))

    # Also run a positive control — simple template should work
    cp_regex = _get_call_regex("cpp")
    m = cp_regex.search("func<int>(x)")
    simple_works = m is not None and m.group(1) == "func"

    all_passed = len(mismatches) > 0 and simple_works
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if all_passed:
    parts = [f"CONFIRMED — nested bracket regex bug reproduced ({len(mismatches)} mismatches)"]
    for lang, text, expected, actual, desc in mismatches:
        parts.append(f"  [{lang}] {desc}: input={text!r} expected={expected!r} actual={actual!r}")
    if simple_works:
        parts.append("  positive control (func<int>(x)) matched correctly")
    print("\n".join(parts))
else:
    print(f"NOT CONFIRMED — mismatches={len(mismatches)} simple_works={simple_works}")
    for lang, text, expected, actual, desc in mismatches:
        print(f"  [{lang}] {desc}: input={text!r} expected={expected!r} actual={actual!r}")
