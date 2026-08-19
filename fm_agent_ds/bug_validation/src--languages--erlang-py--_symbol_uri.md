# Bug Report: _symbol_uri

**Source file:** `src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a non-empty string. When symbol['uri'] exists and is truthy, returns its value. Otherwise, when symbol['location'] exists as a dict and symbol['location']['uri'] is truthy, returns that value. Otherwise, returns fallback unchanged.

---

### Actual Behavior

The function returns the first truthy value among: (1) symbol['uri'] if symbol contains key 'uri' and its value is truthy; (2) symbol['location']['uri'] if symbol contains key 'location', its value is a dictionary, and that dictionary contains key 'uri' with a truthy value; (3) the fallback string (which is non-empty and truthy). Formally: Let result = _symbol_uri(symbol, fallback). Then result = (if 'uri' in symbol and bool(symbol['uri']) is True then symbol['uri'] else (if 'location' in symbol and isinstance(symbol['location'], dict) and 'uri' in symbol['location'] and bool(symbol['location']['uri']) is True then symbol['location']['uri'] else fallback)).

---

## Code Evidence

Line 2: return symbol.get("uri") or (symbol.get("location") or {}).get("uri") or fallback

---

## Trigger Condition

The specification requires that when symbol['location'] does not exist as a dict, fallback should be returned. The code does not check that symbol['location'] is a dict before calling .get('uri') on it. If symbol['location'] is a truthy non-dict (e.g., the string 'not a dict'), the code raises AttributeError, violating the specification's guarantee to return a non-empty string.

---

## How to trigger the bug

The bug is triggered when `_symbol_uri` is called with a `symbol` dict where `symbol['location']` is a truthy non-dict value (e.g., a string, list, or integer). The expression `(symbol.get("location") or {})` short-circuits on the truthy non-dict value, and then `.get("uri")` is called on it, which raises `AttributeError` because strings, lists, and integers have no `.get()` method.

### Inputs

| Parameter | Value |
|-----------|-------|
| `symbol` | `{"location": "not_a_dict_string"}` |
| `fallback` | `"/default/uri"` |

### Expected (spec-correct) Output

`"/default/uri"`

### Actual (buggy) Output

`AttributeError: 'str' object has no attribute 'get'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet:

```python
def _symbol_uri(symbol: dict, fallback: str):
    return symbol.get("uri") or (symbol.get("location") or {}).get("uri") or fallback

symbol = {"location": "not_a_dict_string"}
fallback = "/default/uri"
print(_symbol_uri(symbol, fallback))
// actual (buggy) output: AttributeError: 'str' object has no attribute 'get'
// expected (correct) output: "/default/uri"
```

---

## Probe Script

```python
"""Probe for _symbol_uri bug: truthy non-dict location causes AttributeError."""

import sys

# Exact code from src/languages/erlang.py line 471-472
def _symbol_uri(symbol: dict, fallback: str):
    return symbol.get("uri") or (symbol.get("location") or {}).get("uri") or fallback


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
```

### Probe Output

```

Test 1 (string location): AttributeError raised: 'str' object has no attribute 'get'
Test 2 (list location): AttributeError raised: 'list' object has no attribute 'get'
Test 3 (int location): AttributeError raised: 'int' object has no attribute 'get'
Test 4 (None location): returned '/default/uri' (expected fallback '/default/uri')
Test 5 (no location): returned '/default/uri' (expected fallback '/default/uri')
Test 6 (uri present): returned '/explicit/uri' (expected '/explicit/uri')

CONFIRMED — AttributeError raised when symbol['location'] is a truthy non-dict, violating spec guarantee to return a non-empty string
```
