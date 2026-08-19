"""Probe script for bug: src--scope-py--_name_parts

The function _name_parts splits CamelCase at EVERY uppercase letter instead of
only at lowercase→uppercase transitions. This breaks all-caps acronyms like
'XMLHttp' where 'XML' gets split into single-character fragments that are
filtered out (len > 1), leaving only 'http'.

Spec requires: splitting only at transitions from lowercase to uppercase.
Buggy behavior: splitting at every uppercase letter.
"""

import sys
sys.path.insert(0, '.')

try:
    from src.scope import _name_parts

    name = 'XMLHttp'
    result = _name_parts(name)

    # Spec-correct expected: no lowercase→uppercase transitions in 'XMLHttp',
    # so CamelCase split should produce {'xmlhttp'} only.
    # Buggy behavior: every uppercase gets a '_' prepended, producing
    # 'x', 'm', 'l', 'http' → only 'http' survives len>1 filter.
    # The full lowercased name 'xmlhttp' is always included regardless.

    expected_missing = {'xmlhttp'}
    expected = expected_missing  # full name always included
    buggy_extra = 'http'

    # Bug is confirmed if 'http' appears in result (broken CamelCase split)
    # when it shouldn't (no lower→upper transition exists)
    if buggy_extra in result:
        print(f'CONFIRMED — actual result contains unexpected token {buggy_extra!r} '
              f'from broken CamelCase split | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — result={result!r}, no unexpected CamelCase token found')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
