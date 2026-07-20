#!/usr/bin/env python3
"""Probe for bug: _parse_generic_file KeyError on missing LANG_CONFIG key.

Bug: If _function_spans succeeds for a language not registered in LANG_CONFIG,
the bare dict access LANG_CONFIG[lang_key] raises an unhandled KeyError instead
of gracefully returning (None, None, None).

Strategy: Monkey-patch _function_spans to return success for 'nonexistent_lang',
then call _parse_generic_file. Since _function_spans normally shadows the bug
(it also accesses LANG_CONFIG first), mocking it isolates the unprotected access.
"""

import sys
import os
import tempfile
from pathlib import Path

try:
    from src import scope
    from src import extract

    # Save originals for cleanup
    original_fn_spans = scope._function_spans

    # Monkey-patch _function_spans to return a valid result for 'nonexistent_lang'
    def fake_spans(filepath, lang_key, proj_dir=None):
        if lang_key == 'nonexistent_lang':
            return [('foo', 0, 0)], ['int foo(void) { return 0; }\n']
        return original_fn_spans(filepath, lang_key, proj_dir)

    scope._function_spans = fake_spans

    # Create a temp file (content doesn't matter since spans are mocked)
    tmpdir = tempfile.mkdtemp()
    test_file = Path(tmpdir) / 'test.c'
    test_file.write_text('int foo(void) { return 0; }\n')

    try:
        result = scope._parse_generic_file(test_file, 'nonexistent_lang')
        # If we reach here, no exception was raised — bug NOT confirmed
        print(f'NOT CONFIRMED — returned: {repr(result)}')
    except KeyError as e:
        # KeyError raised on LANG_CONFIG[lang_key] — bug CONFIRMED
        print(f'CONFIRMED — LANG_CONFIG["nonexistent_lang"] raised KeyError: {e}')
    finally:
        # Restore original state
        scope._function_spans = original_fn_spans
        # Cleanup temp files
        import shutil
        shutil.rmtree(tmpdir)

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
