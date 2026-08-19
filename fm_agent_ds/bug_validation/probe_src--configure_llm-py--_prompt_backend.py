"""Probe script for bug: _prompt_backend raises ConfigWizardError on invalid input
instead of reprompting until a valid selection is obtained."""

import io
import sys
from unittest import mock

sys.path.insert(0, 'src')
import configure_llm


def main() -> None:
    mock_prompt = mock.MagicMock(side_effect=["5", "1"])

    suppressed = io.StringIO()
    error = None
    actual = None

    with mock.patch.object(configure_llm, '_prompt', mock_prompt):
        with mock.patch('sys.stdout', suppressed):
            try:
                actual = configure_llm._prompt_backend()
            except configure_llm.ConfigWizardError as exc:
                error = exc
            except Exception as exc:
                error = exc

    if error is not None:
        if isinstance(error, configure_llm.ConfigWizardError):
            print('CONFIRMED - bug reproduced: function terminated with error on invalid input')
            print(f'  Error: {error}')
            print('  Expected: reprompt until valid input (spec: "does not return until valid")')
            print('  Actual: raised ConfigWizardError on first invalid input "5"')
        else:
            print(f'ERROR: {error}')
    else:
        expected = 'opencode'
        if actual == expected:
            print('NOT CONFIRMED - function reprompted and returned correct result')
            print(f'  Result: {actual!r} (expected {expected!r} for input "1")')
        else:
            print(f'NOT CONFIRMED - unexpected result: {actual!r} (expected {expected!r})')


if __name__ == '__main__':
    main()
