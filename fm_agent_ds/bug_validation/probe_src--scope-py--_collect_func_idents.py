"""Probe script for bug ID: src--scope-py--_collect_func_idents

Tests whether _collect_func_idents correctly collects exception types from
ast.Tuple nodes in except clauses (e.g., except (ValueError, TypeError):).
"""

import ast
import os
import sys
import tempfile
from textwrap import dedent

# Use a temp directory for any probe-owned files to satisfy the self-validation guard
_PROBE_TMP = tempfile.mkdtemp(prefix="probe__collect_func_idents_")

try:
    # Ensure the repo root is on the path (run from repo root, per Step 2d)
    _cwd = os.getcwd()
    if _cwd not in sys.path:
        sys.path.insert(0, _cwd)

    from src.scope import _collect_func_idents

    # Create a test function AST with tuple except clauses
    code = dedent("""\
    def test_tuple_except():
        try:
            x = 1 / 0
        except (ValueError, TypeError):
            pass
        except (OSError, IOError) as e:
            pass
        except RuntimeError:
            pass
    """)

    tree = ast.parse(code)
    func_node = tree.body[0]

    source_lines = code.strip().split('\n')

    _idents, _body_words, exc_types = _collect_func_idents(func_node, source_lines)

    # The spec requires all caught exception types from except clauses.
    # The tuple-form except (ValueError, TypeError) should yield 'valueerror' and
    # 'typeerror'. RuntimeError (single Name) should work as expected.
    expected = {'valueerror', 'typeerror', 'oserror', 'ioerror', 'runtimeerror'}

    missing = expected - exc_types

    if missing:
        print(f'CONFIRMED — exc_types missing: {sorted(missing)} '
              f'| actual exc_types: {sorted(exc_types)}')
    else:
        print(f'NOT CONFIRMED — all expected exc types present: '
              f'{sorted(exc_types)}')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    # Clean up temp directory
    try:
        os.rmdir(_PROBE_TMP)
    except OSError:
        pass
