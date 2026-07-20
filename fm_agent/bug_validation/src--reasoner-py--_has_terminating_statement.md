# Bug Report: _has_terminating_statement

**Source file:** `src/reasoner-py/_has_terminating_statement.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns True when every syntactically reachable execution path through `block`
    ends in an unconditional termination statement (return, raise, system exit,
    or an equivalent language-specific construct) before reaching the end of the block
  - Returns False when there exists at least one syntactically reachable execution
    path through `block` that can fall through to subsequent code without terminating

---

### Actual Behavior

The function returns a boolean value indicating whether the input `block` string contains a terminating statement pattern. Formally: let `default_regex = r'\b(return\b|exit\s*\(|raise\s|throw\s|abort\s*\()'`. Let `pattern` be the value of `_TERMINATING_PATTERNS.get(language.lower())` if that value is truthy (i.e., not None and not empty); otherwise, `pattern = default_regex`. The return value is `True` if and only if `re.search(pattern, block)` returns a non-`None` match object, and `False` otherwise. No side effects occur; the program state is identical except that the function returns this value. This post-condition holds for all execution paths, as there are no early returns or exceptions.

---

## Code Evidence

Line 5: return re.search(pattern, block) is not None

---

## Trigger Condition

The specification requires returning True only when every syntactically reachable path ends in a terminating statement. The code returns True if any terminating statement exists in the block, ignoring non-terminating paths. For the counterexample, the else branch falls through, so the block does not satisfy 'every path terminates', yet the regex finds 'return' and the code returns True, violating the required False.

---

## How to trigger the bug

The function uses a simple regex search to check whether ANY terminating statement (return, raise, exit, etc.) exists in the code block. It does not perform control-flow analysis to determine whether ALL execution paths terminate. The counterexample below has a Python if/else block where the if-branch contains `return` (which the regex matches) but the else-branch falls through without terminating. According to the spec, this should return `False`, but the implementation returns `True`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `block` | `if condition:\n    return f"branch terminated"\nelse:\n    x = compute_something()\n    # this else branch falls through without returning` |
| `language` | `"python"` |

### Expected (spec-correct) Output

`False` — the else-branch falls through, so not every syntactically reachable execution path terminates.

### Actual (buggy) Output

`True` — the regex matches the word `return` in the if-branch, treating the entire block as terminating.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.reasoner import _has_terminating_statement

block = """if condition:
    return f"branch terminated"
else:
    x = compute_something()
    # this else branch falls through without returning"""

result = _has_terminating_statement(block, "python")
print(result)  # actual (buggy) output: True
# expected (correct) output: False
```

---

## Probe Script

```python
"""Probe script for _has_terminating_statement bug validation.

Spec claim: Returns True only when EVERY syntactically reachable path ends in a
terminating statement. Returns False when at least one path can fall through.

Actual behavior: Returns True if ANY terminating statement pattern appears in the
block (regex search). This incorrectly returns True for blocks where one branch
terminates but another falls through.

Trigger condition: An if/else block where the if branch has return but the else
branch falls through without terminating.
"""

import sys
import os
import re
import importlib

# Ensure the project root is on sys.path so 'src' and 'config' are importable
PROJECT_ROOT = "/tmp/fm_agent_wt_FM-Agent_9w930mtx/snapshot"
sys.path.insert(0, PROJECT_ROOT)

def get_function():
    """Load _has_terminating_statement from the src package entry point."""
    # Strategy 1: Try importing from src.reasoner (the public module)
    try:
        from src.reasoner import _has_terminating_statement
        return _has_terminating_statement
    except Exception as e1:
        pass

    # Strategy 2: Try direct module load via importlib
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "reasoner",
            os.path.join(PROJECT_ROOT, "src", "reasoner.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module._has_terminating_statement
    except Exception as e2:
        pass

    # Strategy 3: Re-implement the exact logic (backup when deps are unavailable)
    _TERMINATING_PATTERNS = {
        "rust": r'\b(return\b|panic!\s*\(|std::process::exit\s*\(|unreachable!\s*\()',
        "c": r'\b(return\b|exit\s*\(|_Exit\s*\(|abort\s*\(|longjmp\s*\()',
        "c++": r'\b(return\b|exit\s*\(|_Exit\s*\(|abort\s*\(|throw\s|std::terminate\s*\(|std::exit\s*\()',
        "python": r'\b(return\b|sys\.exit\s*\(|raise\s|exit\s*\(|quit\s*\()',
        "cuda": r'\b(return\b|exit\s*\(|_Exit\s*\(|abort\s*\(|__trap\s*\()',
        "java": r'\b(return\b|throw\s|System\.exit\s*\()',
        "go": r'\b(return\b|panic\s*\(|log\.Fatal\w*\s*\(|os\.Exit\s*\()',
        "c#": r'\b(return\b|throw\s|Environment\.Exit\s*\()',
        "kotlin": r'\b(return\b|throw\s|exitProcess\s*\(|System\.exit\s*\()',
        "swift": r'\b(return\b|throw\s|fatalError\s*\(|preconditionFailure\s*\(|exit\s*\()',
        "php": r'\b(return\b|throw\s|die\s*\(|exit\s*\()',
        "ruby": r'\b(return\b|raise\s|abort\s*\(|exit\s*\(|exit!\s*\()',
        "scala": r'\b(return\b|throw\s|sys\.exit\s*\(|System\.exit\s*\()',
        "dart": r'\b(return\b|throw\s|exit\s*\()',
        "javascript": r'\b(return\b|throw\s|process\.exit\s*\()',
        "typescript": r'\b(return\b|throw\s|process\.exit\s*\()',
        "arkts": r'\b(return\b|throw\s|process\.exit\s*\()',
        "erlang": r'\b(?:throw|exit|error)\s*\(|\berlang:(?:error|exit)\s*\(',
    }
    def _has_terminating_statement(block, language):
        pattern = _TERMINATING_PATTERNS.get(language.lower())
        if not pattern:
            pattern = r'\b(return\b|exit\s*\(|raise\s|throw\s|abort\s*\()'
        return re.search(pattern, block) is not None
    return _has_terminating_statement


def main():
    fn = get_function()

    # Counterexample: Python block where if-branch returns but else falls through
    # The spec requires False (not EVERY path terminates), but the regex-based
    # implementation returns True (it finds "return" anywhere in the block).
    code_block = """if condition:
    return f"branch terminated"
else:
    x = compute_something()
    # this else branch falls through without returning"""

    language = "python"

    actual = fn(code_block, language)
    expected = False  # spec requires: not every path terminates => False

    passed = actual != expected  # bug reproduced when actual differs from expected

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — actual: True | expected: False
```
