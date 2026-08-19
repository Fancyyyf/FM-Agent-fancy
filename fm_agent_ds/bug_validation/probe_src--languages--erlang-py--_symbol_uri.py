"""Probe for _symbol_uri bug: truthy non-dict location causes AttributeError."""

import sys

# Exact code from src/languages/erlang.py line 471-472
def _symbol_uri(symbol: dict, fallback: str):
    return symbol.get("uri") or (symbol.get("location") or {}).get("uri") or fallback


def run_test(description, symbol, fallback, expect_fallback: bool):
    """Run a single test case. If expect_fallback is True, we expect the fallback
    to be returned (not an exception). If the function raises AttributeError when
    it should have returned the fallback, the bug is confirmed."""
    try:
        actual = _symbol_uri(symbol, fallback)
        if expect_fallback:
            if actual != fallback:
                print(f"  WARN: got {actual!r}, expected fallback {fallback!r}")
                return False
        return True  # no crash = potential NOT CONFIRMED
    except AttributeError as e:
        if expect_fallback:
            print(f"  CONFIRMED BUG: AttributeError on {description}: {e}")
            return False  # bug triggered
        else:
            print(f"  ERROR (unexpected crash): {e}")
            return False


def main():
    confirmed = False
    details = []

    # Test 1: location is a truthy string (the trigger condition)
    symbol1 = {"location": "not_a_dict_string"}
    fallback1 = "/default/uri"
    try:
        _symbol_uri(symbol1, fallback1)
        details.append("Test 1 (string location): NO exception — returned value instead of crashing")
    except AttributeError as e:
        confirmed = True
        details.append(f"Test 1 (string location): AttributeError raised: {e}")

    # Test 2: location is a truthy list
    symbol2 = {"location": ["elem1", "elem2"]}
    fallback2 = "/default/uri"
    try:
        _symbol_uri(symbol2, fallback2)
        details.append("Test 2 (list location): NO exception")
    except AttributeError as e:
        confirmed = True
        details.append(f"Test 2 (list location): AttributeError raised: {e}")

    # Test 3: location is a truthy integer
    symbol3 = {"location": 42}
    fallback3 = "/default/uri"
    try:
        _symbol_uri(symbol3, fallback3)
        details.append("Test 3 (int location): NO exception")
    except AttributeError as e:
        confirmed = True
        details.append(f"Test 3 (int location): AttributeError raised: {e}")

    # Test 4: location is None (should work, uses fallback)
    symbol4 = {"location": None}
    fallback4 = "/default/uri"
    try:
        result4 = _symbol_uri(symbol4, fallback4)
        details.append(f"Test 4 (None location): returned {result4!r} (expected fallback {fallback4!r})")
    except Exception as e:
        details.append(f"Test 4 (None location): ERROR: {e}")

    # Test 5: no location key (should work, uses fallback)
    symbol5 = {}
    fallback5 = "/default/uri"
    try:
        result5 = _symbol_uri(symbol5, fallback5)
        details.append(f"Test 5 (no location): returned {result5!r} (expected fallback {fallback5!r})")
    except Exception as e:
        details.append(f"Test 5 (no location): ERROR: {e}")

    # Test 6: uri present (should use uri)
    symbol6 = {"uri": "/explicit/uri"}
    fallback6 = "/default/uri"
    try:
        result6 = _symbol_uri(symbol6, fallback6)
        details.append(f"Test 6 (uri present): returned {result6!r} (expected {symbol6['uri']!r})")
    except Exception as e:
        details.append(f"Test 6 (uri present): ERROR: {e}")

    print()
    for d in details:
        print(d)

    print()
    if confirmed:
        print("CONFIRMED — AttributeError raised when symbol['location'] is a truthy non-dict, violating spec guarantee to return a non-empty string")
    else:
        print("NOT CONFIRMED — no AttributeError was raised for truthy non-dict location values")


if __name__ == "__main__":
    main()
