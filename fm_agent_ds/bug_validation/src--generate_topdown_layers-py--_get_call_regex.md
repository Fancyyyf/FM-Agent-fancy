# Bug Report: _get_call_regex

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/generate_topdown_layers-py/_get_call_regex.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a compiled regular expression. When applied to source text from which comments have been stripped, the first capture group of each match yields a bare-word identifier that precedes an opening parenthesis '(' at a syntactic call position for the language identified by lang_key. Any type-argument syntax (e.g., angle-bracket-delimited or square-bracket-delimited generic parameters) permitted by the language between the identifier and the parenthesis is tolerated. Whitespace is allowed between the identifier, optional type arguments, and the parenthesis.

---

### Actual Behavior

Returns a compiled regular expression (re.Pattern) for matching function call sites in the language given by lang_key. The returned regex captures the function name in group 1 and ensures an opening parenthesis follows. The exact pattern depends on lang_key: for 'cpp','c','java','typescript','javascript','cuda','arkts' it includes optional template arguments `<...>`; for 'rust' it includes optional turbofish `::<...>`; for 'go' it includes optional type parameters `[...]`; and for any other lang_key (e.g., 'python','ruby') it matches a plain identifier followed by optional whitespace and '('. Formally: let L = {'cpp','c','java','typescript','javascript','cuda','arkts'}, then (lang_key  L)  return = re.compile(r"\\b(\\w+)\\s*(?:<[^>]*>)?\\s*\\(")  (lang_key = 'rust')  return = re.compile(r"\\b(\\w+)\\s*(?:::<[^>]*>)?\\s*\\(")  (lang_key = 'go')  return = re.compile(r"\\b(\\w+)\\s*(?:\\[[^\\]]*\\])?\\s*\\(")  (lang_key  L  {'rust','go'})  return = re.compile(r"\\b(\\w+)\\s*\\(").

---

## Code Evidence

Line 5: return re.compile(r"\b(\w+)\s*(?:<[^>]*>)?\s*\(")
Line 8: return re.compile(r"\b(\w+)\s*(?:::<[^>]*>)?\s*\(")
Line 11: return re.compile(r"\b(\w+)\s*(?:\[[^\]]*\])?\s*\(")

---

## Trigger Condition

The regex patterns use [^>]* and [^\]]* which do not allow nested brackets typical of template/generic arguments in C++, Java, Rust, Go, etc., thus failing to match valid call sites with nested type arguments like foo<A<B>>(x).

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| lang_key (C++) | `"cpp"`, input string: `"foo<A<B>>(x)"` |
| lang_key (Rust) | `"rust"`, input string: `"bar::<Vec<u8>>(x)"` |
| lang_key (Go) | `"go"`, input string: `"fn[map[string]int](x)"` |

### Expected (spec-correct) Output

The regex should match and capture the function name in group 1:
- C++: `"foo"` from `foo<A<B>>(x)`
- Rust: `"bar"` from `bar::<Vec<u8>>(x)`
- Go: `"fn"` from `fn[map[string]int](x)`

### Actual (buggy) Output

All three inputs produce **no match** (regex.search returns None). The character classes `[^>]*` and `[^\]]*` greedily consume characters but stop at the first `>` or `]`, leaving the text position at a `>` or `]` character instead of `(`, so the regex fails to find the opening parenthesis.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, ".")

from src.generate_topdown_layers import _get_call_regex

# C++ nested template — should match, but returns None
regex = _get_call_regex("cpp")
m = regex.search("foo<A<B>>(x)")
# actual (buggy) output: None (no match)
# expected (correct) output: "foo"

# Rust nested turbofish — should match, but returns None
regex = _get_call_regex("rust")
m = regex.search("bar::<Vec<u8>>(x)")
# actual (buggy) output: None (no match)
# expected (correct) output: "bar"

# Go nested type params — should match, but returns None
regex = _get_call_regex("go")
m = regex.search("fn[map[string]int](x)")
# actual (buggy) output: None (no match)
# expected (correct) output: "fn"
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — nested bracket regex bug reproduced (3 mismatches)
  [cpp] cpp nested template args: input='foo<A<B>>(x)' expected='foo' actual=None
  [rust] rust nested turbofish: input='bar::<Vec<u8>>(x)' expected='bar' actual=None
  [go] go nested type params: input='fn[map[string]int](x)' expected='fn' actual=None
  positive control (func<int>(x)) matched correctly
```
