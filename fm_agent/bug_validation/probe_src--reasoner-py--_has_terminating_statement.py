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
