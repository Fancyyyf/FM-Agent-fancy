import sys
import ast

try:
    from src.scope import _collect_calls
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Construct a decorated function AST to test whether _collect_calls
# incorrectly collects call-site names from decorators.
#
# Python source equivalent:
#   @mydecorator(42)
#   def foo(a, b):
#       bar()
#
# The decorator @mydecorator(42) is a Call node in decorator_list,
# NOT part of the function body. Per spec, only 'bar' should be collected.

source = """
@mydecorator(42)
def foo(a, b):
    bar()
"""

tree = ast.parse(source)
func_node = tree.body[0]  # The FunctionDef node

calls = _collect_calls(func_node)

# Expected (spec-correct): only calls within the function body → {'bar'}
# Actual (buggy): ast.walk() includes decorator_list → {'mydecorator', 'bar'}
expected = {'bar'}
actual = calls
passed = actual != expected  # True → bug reproduced (actual has extra names)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
