import sys
import os
import ast

# Add snapshot root to sys.path so `from src.scope import ...` resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.scope import _extract_classes

    # Python source with a module-level class containing a nested class
    source = (
        "class Outer:\n"
        "    '''Outer docstring'''\n"
        "    def outer_method(self):\n"
        "        '''outer method doc'''\n"
        "        pass\n"
        "    \n"
        "    class Inner:\n"
        "        '''Inner docstring'''\n"
        "        def inner_method(self):\n"
        "            '''inner method doc'''\n"
        "            pass\n"
        "\n"
        "def standalone():\n"
        "    pass\n"
    )

    tree = ast.parse(source)
    source_lines = source.split('\n')

    classes = _extract_classes(tree, source_lines)
    class_names = [c['name'] for c in classes]

    # Bug 1: Nested class 'Inner' should NOT be in the output.
    # Spec says "one per class defined at module scope in tree".
    # ast.walk visits ALL ClassDef nodes including nested ones.
    bug_nested = 'Inner' in class_names

    # Bug 2: Per-method detail sub-dicts (name, start, end, calls, idents,
    # body_words, exc_types, docstring) are entirely missing from the output.
    # The class dict should contain these per-method detail keys alongside
    # name, lineno, end_lineno, docstring, method_linenos.
    per_method_keys = {'start', 'end', 'calls', 'idents', 'body_words', 'exc_types'}
    bug_missing_details = False
    for cls in classes:
        cls_keys = set(cls.keys())
        # If none of the per-method detail keys are present, details are missing
        if not per_method_keys & cls_keys:
            bug_missing_details = True
            break

    # Bug is confirmed if either issue exists
    if bug_nested or bug_missing_details:
        reasons = []
        if bug_nested:
            reasons.append(
                f"nested class 'Inner' included in output "
                f"(spec requires module-scope classes only)"
            )
        if bug_missing_details:
            reasons.append(
                f"per-method detail sub-dicts (start, end, calls, idents, "
                f"body_words, exc_types, docstring) missing from output"
            )
        print(f"CONFIRMED — {'; '.join(reasons)}")
        print(f"  actual classes: {class_names}")
        print(f"  expected (spec): ['Outer'] (module-scope only, excluding nested Inner)")
        print(f"  actual class keys: {[sorted(c.keys()) for c in classes]}")
        print(f"  expected keys per spec: name, lineno, end_lineno, docstring, "
              f"method_linenos + per-method detail sub-dicts")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {class_names}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
