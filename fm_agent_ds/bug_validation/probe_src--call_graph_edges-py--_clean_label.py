import sys
sys.path.insert(0, "src")

try:
    from call_graph_edges import normalize_fqn_label

    actual = normalize_fqn_label("'ab;'")
    # The spec says _clean_label returns a string with no trailing semicolon.
    # For input "'ab;'", the correct output should have quotes removed AND
    # the trailing semicolon removed: "ab"
    expected = "ab"
    passed = actual != expected
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
