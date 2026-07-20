# [SPEC]
# Unit: src/languages/erlang-py/__init___2.py
#
# ElpClient.__init__(self, proj_dir: str)
#
# Pre-condition:
#   - proj_dir is a non-empty string representing a filesystem path
#
# Post-condition:
#   - self.proj_dir is the absolute, normalized path derived from proj_dir via
#     os.path.abspath resolution (relative path components such as "." and ".."
#     are resolved; symlinks are NOT canonicalized)
#   - self.root_uri is the file:// URI representation of self.proj_dir
#   - self.timeout is an integer ≥ 1 representing the maximum number of seconds
#     the client will wait for any single LSP response or server status transition
#   - self._messages is a new, empty thread-safe queue capable of concurrent
#     enqueue and dequeue operations from multiple threads
#   - self._next_id is initialized to 1, serving as a monotonically increasing
#     JSON-RPC message identifier counter
#   - self._status is initialized to None, indicating that the ELP server has not
#     yet reported its running status
#   - self._write_lock is a new, unacquired threading.Lock instance used to
#     serialize writes to the subprocess stdin pipe
#   - self._proc is initialized to None, indicating that no subprocess has been
#     started
#   - self._reader is initialized to None, indicating that no reader thread has
#     been created
#   - No subprocess is started, no I/O resources are acquired, and no threads are
#     spawned during construction
# [SPEC]

# [INFO]
# _timeout_seconds() -> int
#   Pre-condition: None (configured via environment variable or a built-in default)
#   Post-condition: Returns an integer ≥ 1 representing the maximum number of
#     seconds to wait for a single LSP operation
# [INFO]

    def __init__(self, proj_dir: str):
        self.proj_dir = os.path.abspath(proj_dir)
        self.root_uri = Path(self.proj_dir).as_uri()
        self.timeout = _timeout_seconds()
        self._messages: queue.Queue = queue.Queue()
        self._next_id = 1
        self._status = None
        self._write_lock = threading.Lock()
        self._proc = None
        self._reader = None
