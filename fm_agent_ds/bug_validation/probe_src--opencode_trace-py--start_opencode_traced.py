import sys
import subprocess
import threading
import os

# Add repo root to path so 'src' package is importable
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    import src.opencode_trace as mod
except Exception as e:
    print(f'ERROR: import failed: {e}')
    sys.exit(1)

# Mock subprocess.Popen to avoid actually launching opencode
class MockPopen:
    def __init__(self, *args, **kwargs):
        self.pid = 12345
        self.returncode = None
        self.stdout = None
        self.stdin = None
    def poll(self):
        return self.returncode
    def wait(self, timeout=None):
        return 0

# Mock daemon threads
class MockThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
    def start(self):
        pass
    def join(self, timeout=None):
        pass

def mock_start_opencode_process(proj_dir, work_dir, event_id, command, trace_log_path):
    return MockPopen(), MockThread(), None

def mock_new_event_id(prefix):
    return f'{prefix}_deadbeef_cafe_1234567890abcdef'

def mock_utc_now_iso():
    return '2024-01-01T00:00:00Z'

# Apply mocks
mod._start_opencode_process = mock_start_opencode_process
mod.new_event_id = mock_new_event_id
mod.utc_now_iso = mock_utc_now_iso

actual = None
expected = None
passed = False

try:
    result = mod.start_opencode_traced(
        proj_dir='.',
        work_dir='/tmp/fm_agent_probe_test',
        command=['echo', 'hello'],
        stage='test',
    )

    # The spec claim is: returned record has error=None
    # The bug claim is: returned instance lacks the error attribute
    actual_has_error = hasattr(result, 'error')
    actual_error_value = result.error if actual_has_error else 'ATTRIBUTE_MISSING'

    expected_has_error = True
    expected_error_value = None

    # Bug is CONFIRMED if error attribute is missing OR error is not None
    passed = not actual_has_error or actual_error_value is not None

    actual = f'has error attr={actual_has_error}, error_value={actual_error_value!r}'
    expected = f'has error attr={expected_has_error}, error_value={expected_error_value!r}'

except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual} | expected: {expected}')
else:
    print(f'NOT CONFIRMED — actual: {actual} | expected: {expected}')
