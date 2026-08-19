import sys
import os

# The project root is where we run the probe from. Add it to the Python path
# so that "from src.languages.python import function_spans" resolves.
proj_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, proj_dir)

try:
    from src.languages.python import function_spans
except Exception as e:
    print(f'ERROR: Failed to import function_spans: {e}')
    sys.exit(1)

# Use src/prompts.py which has _nonempty_string (line 64-65) nested inside
# _parse_spec_check_json (line 32-94).
# Codegraph stores nested functions with qualified_name like
# "_parse_spec_check_json::_nonempty_string", which _extraction_ident
# preserves in the returned name.
filepath = os.path.join(proj_dir, 'src', 'prompts.py')

try:
    spans = function_spans(proj_dir, filepath)

    if spans is None:
        print('NOT CONFIRMED — function_spans returned None (codegraph not available or file not indexed)')
        sys.exit(0)

    # The spec says "one per top-level function". A nested function
    # (defined inside another function) should NOT appear. The _extraction_ident
    # function in codegraph.py returns "Parent::Nested" for nested functions,
    # keeping the qualified scope. Top-level functions have no "::" in their name.
    all_names = [name for name, _start, _end in spans]
    nested = [n for n in all_names if '::' in n]
    top_level = [n for n in all_names if '::' not in n]

    has_nested = len(nested) > 0

    if has_nested:
        # This is the buggy behavior: nested functions are returned when the
        # spec says only top-level functions should be.
        print(f'CONFIRMED — nested function(s) returned by function_spans')
        print(f'  Top-level functions: {top_level}')
        print(f'  Nested functions (BUG — should not be present): {nested}')
        print(f'  Spec requires only top-level functions, but {len(nested)} nested function(s) are returned.')
    else:
        print(f'NOT CONFIRMED — no nested functions found.')
        print(f'  All functions: {all_names}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
