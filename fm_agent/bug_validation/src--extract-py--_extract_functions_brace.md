# Bug Report: _extract_functions_brace

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/extract-py/_extract_functions_brace.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of (raw_name, start, end) tuples, one per top-level function definition detected in lines, ordered by first appearance in the source
  - Each tuple describes a contiguous span: start is the 0-based index of the first line of the function definition, end is the 0-based index of the last line of the function body (containing the matching closing brace of the body), satisfying 0 <= start <= end < len(lines)
  - A function definition is identified by a language-specific declarator pattern at the outermost nesting level, followed by a brace-delimited body
  - The raw_name is the unqualified function name as it appears in the source text
  - Returned spans are non-overlapping: no line index belongs to more than one span
  - Lines inside syntactically well-formed comments (both line comments and block comments delimited by the language's comment syntax) are excluded from function-definition detection
  - Lines matching the skip-prefix and skip-keyword patterns defined in lang_cfg are excluded from function-definition detection
  - Language-specific exclusion rules (e.g., namespace and class declarations, constexpr variables, test-annotated functions) are applied so that non-function constructs are not misidentified as function definitions
  - For C and C++, only source lines at the leftmost indent level are considered as function-definition candidates
  - When no function definitions are detected, returns an empty list

---

### Actual Behavior

After execution of the code block (lines 121173), the program state satisfies the following. This block is reached only from Path B2 of the preceding block (lines 81120), i.e., `lang_key == "rust"`, the `fn` regex match succeeded (`m` is not `None`), and `has_test_attr` is either `True` or `False`. The block unconditionally executes lines 121126, finding the opening brace and skipping the entire brace-delimited scope. Lines 127173 are dead code because line 126 always transfers control out of the block via `continue`.

**Effects on variables:**
- `functions` is unchanged: `functions = old(functions)`.
- `has_test_attr` is unchanged: `has_test_attr = old(has_test_attr)`.
- `sig_end` and `i` are updated according to whether an opening brace `{` is found within the next 10 lines starting from `i`.
  - If there exists an index `k` with `old(i)  k < min(old(i) + 10, len(lines))` such that `'{' in lines[k]`, then `sig_end = k` and `i = _find_brace_end(lines, k) + 1`.
  - Otherwise, the loop completes without finding `{`; `sig_end` retains its previous value `old(sig_end)`, and `i` is set to `_find_brace_end(lines, old(sig_end)) + 1` (this case may lead to undefined behaviour if `old(sig_end)` does not contain `{`; under normal execution a `{` is always found).
- All other variables (`name`, `m`, `stripped`, etc.) remain unchanged from the state before line 121.
- A `continue` statement on line 126 transfers control to the top of the enclosing loop; the block does not return.

**Formal post-condition:**
Let the state before executing line 121 be denoted by `old`. From the pre-condition we have `old(lang_key) = "rust"` and `old(m)  None`. Define:
- `i0 = old(i)`
- `F = old(functions)`
- `h = old(has_test_attr)`
- `sig0 = old(sig_end)`
- `N = min(i0 + 10, len(old(lines)))`
- `K = {k | i0  k < N  '{'  old(lines)[k]}`  (set of indices with an opening brace in the scanned range)

The state after the block (at the point of `continue`) satisfies:
- `functions = F` (unchanged)
- `has_test_attr = h` (unchanged)
- If `K` is non-empty: `sig_end = min(K)`, `i = _find_brace_end(lines, min(K)) + 1`
- If `K` is empty: `sig_end = sig0`, `i = _find_brace_end(lines, sig0) + 1`

---

## Code Evidence

Line 121: for look in range(i, min(i + 10, len(lines))):
Line 122: if '{' in lines[look]:
Line 123: sig_end = look
Line 124: break
Line 125: i = _find_brace_end(lines, sig_end) + 1
Line 126: continue

---

## Trigger Condition

The code unconditionally executes lines 121126 for every Rust function definition that reaches this block, skipping the entire function body without adding it to the functions list. This omits valid top-level Rust functions from the output, violating the specification that requires a tuple for each detected function definition.

---

## How to trigger the bug

The bug claim is that in the Rust branch of `_extract_functions_brace`, lines 121-126 unconditionally execute a `continue` before the function can be appended to the `functions` list, making lines 127-173 dead code.

Upon inspection of the actual source code (`src/extract.py` lines 441-489), the `continue` on the line equivalent to 126 (line 479 in the source, line 169 in the extracted copy) is **inside** the `if has_test_attr:` block. When `has_test_attr` is `False`, execution falls through to `functions.append()` on line 487. The function IS correctly added to the output list.

The line numbering in the bug report (121-126) corresponds to the Go section of the extracted function file, not the Rust section. The Rust section spans lines 131-179 and includes both the `#[test]` skip path (lines 162-169) and the normal function extraction path (lines 170-179).

### Inputs

Test input (Rust source lines):
```
#[derive(Debug)]
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[test]
fn test_add() {
    assert_eq!(add(1, 2), 3);
}

fn main() {
    println!("{}", add(1, 2));
}
```

### Expected (spec-correct) Output

`[('add', 1, 3), ('main', 10, 12)]` — two functions extracted, `#[test]`-annotated function skipped per spec.

### Actual (buggy) Output

`[('add', 1, 3), ('main', 10, 12)]` — exactly matches expected. The code behaves correctly.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.extract import _extract_functions_brace, LANG_CONFIG

rust_lines = [
    '#[derive(Debug)]',
    'pub fn add(a: i32, b: i32) -> i32 {',
    '    a + b',
    '}',
    '',
    '#[test]',
    'fn test_add() {',
    '    assert_eq!(add(1, 2), 3);',
    '}',
    '',
    'fn main() {',
    '    println!("{}", add(1, 2));',
    '}',
]

result = _extract_functions_brace(rust_lines, 'rust', LANG_CONFIG['rust'])
print(result)
# actual output: [('add', 1, 3), ('main', 10, 12)]
# expected output: [('add', 1, 3), ('main', 10, 12)]
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on sys.path so `import src.extract` resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.extract import _extract_functions_brace, LANG_CONFIG
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

rust_lines = [
    '#[derive(Debug)]',
    'pub fn add(a: i32, b: i32) -> i32 {',
    '    a + b',
    '}',
    '',
    '#[test]',
    'fn test_add() {',
    '    assert_eq!(add(1, 2), 3);',
    '}',
    '',
    'fn main() {',
    '    println!("{}", add(1, 2));',
    '}',
]

lang_key = 'rust'
lang_cfg = LANG_CONFIG['rust']

try:
    result = _extract_functions_brace(rust_lines, lang_key, lang_cfg)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

print(f'Result: {result}')
print(f'Number of functions found: {len(result)}')

names = [name for name, _, _ in result]

# Check that "test_add" is NOT in the results (it has #[test])
test_add_skipped = all(name != 'test_add' for name in names)

# Check that "add" and "main" ARE in the results
add_found = any(name == 'add' for name in names)
main_found = any(name == 'main' for name in names)

all_ok = test_add_skipped and add_found and main_found and len(result) == 2

if all_ok:
    print(f'NOT CONFIRMED — all assertions passed: add_found={add_found}, main_found={main_found}, test_add_skipped={test_add_skipped}, count={len(result)}')
else:
    print(f'CONFIRMED — add_found={add_found}, main_found={main_found}, test_add_skipped={test_add_skipped}, result={result!r}')
```

### Probe Output

```
Result: [('add', 1, 3), ('main', 10, 12)]
Number of functions found: 2
NOT CONFIRMED — all assertions passed: add_found=True, main_found=True, test_add_skipped=True, count=2
```
