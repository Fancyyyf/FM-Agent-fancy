"""Probe script for bug: _select_functions_by_source missing return statement.

Bug claim: After reaching line 40, the function falls off and returns None
instead of the required (all_by_source, keep_by_source) tuple.

Verification approach: static inspection of the function source code.
"""

import ast
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_FILE = REPO_ROOT / "src" / "entry_reasoning_pipeline.py"


def _find_function_node(tree, func_name):
    """Find the AST FunctionDef node for the given function name."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            return node
    return None


def _has_explicit_return(func_node):
    """Check if the function body contains at least one explicit Return statement."""
    for node in ast.walk(func_node):
        if isinstance(node, ast.Return) and node.value is not None:
            return True
    return False


def _find_empty_phase_files_handler(func_node):
    """Find the if-not-phase_files block and check it has a raise or return.

    Returns (found: bool, has_raise_or_return: bool).
    """
    for node in ast.walk(func_node):
        if not isinstance(node, ast.If):
            continue
        # Check if test is: not phase_files  (UnaryOp(Not(), Name('phase_files')))
        test = node.test
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            if isinstance(test.operand, ast.Name) and test.operand.id == "phase_files":
                # Check if body contains a Raise or Return
                for stmt in node.body:
                    if isinstance(stmt, (ast.Raise, ast.Return)):
                        return True, True
                return True, False
    return False, False


def main():
    try:
        source = SOURCE_FILE.read_text()
        tree = ast.parse(source)
        func = _find_function_node(tree, "_select_functions_by_source")

        if func is None:
            print("ERROR: _select_functions_by_source not found in source")
            sys.exit(1)

        # Check 1: Does function have an explicit return?
        has_return = _has_explicit_return(func)

        # Check 2: Does the empty phase_files guard raise/return?
        found_guard, has_raise = _find_empty_phase_files_handler(func)

        # Bug is CONFIRMED if:
        #   - No explicit return (function falls off => returns None)
        #   - OR the empty phase_files guard has no raise/return (falls through)
        bug_confirmed = not has_return or (found_guard and not has_raise)

        if bug_confirmed:
            print(f"CONFIRMED — has_return={has_return}, found_guard={found_guard}, has_raise={has_raise}")
        else:
            print(f"NOT CONFIRMED — has_return={has_return}, found_guard={found_guard}, has_raise={has_raise}")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
