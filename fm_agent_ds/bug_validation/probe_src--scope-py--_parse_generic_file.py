import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

try:
    # When run from repo root, CWD must be on sys.path
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    # Load package via its public entry point
    import src.scope as scope
    import src.extract as extract

    # Create a temporary directory for test fixtures
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_lang = 'fake_lang_xyz'  # NOT in LANG_CONFIG
        fake_ext = 'fakeext'

        # Create a temp source file with the fake extension
        dummy_path = Path(tmpdir) / f'test.{fake_ext}'
        dummy_path.write_text('void foo() { return; }\n')

        # Monkey-patch _function_spans to succeed with any lang_key
        # (returns one dummy span and one line of raw text)
        # NOTE: scope imports _function_spans as a local name, so we must
        # patch scope._function_spans, not extract._function_spans.
        def patched_function_spans(filepath, lang_key, proj_dir=None):
            return [('foo', 0, 1)], ['void foo() { return; }\n']

        with patch.object(scope, '_function_spans', side_effect=patched_function_spans), \
             patch.dict(extract.EXT_TO_LANG, {fake_ext: fake_lang}, clear=False):

            actual_error = None
            try:
                result = scope.rank_functions_in_file(
                    filepath=str(dummy_path),
                    src_path=dummy_path,
                    issue='test bug',
                    signals={},
                )
                actual_error = f'No error — returned: {type(result).__name__}'
            except KeyError as e:
                actual_error = f'KeyError: {e}'
            except Exception as e:
                actual_error = f'{type(e).__name__}: {e}'

        # Restore EXT_TO_LANG (patch.dict auto-restores)

        expected = f'KeyError: \'{fake_lang}\''
        if actual_error and fake_lang in str(actual_error) and 'KeyError' in str(actual_error):
            print(f'CONFIRMED — KeyError raised for unknown lang_key "{fake_lang}" instead of returning (None, None, None): {actual_error}')
        else:
            print(f'NOT CONFIRMED — Expected KeyError for "{fake_lang}" but got: {actual_error}')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
