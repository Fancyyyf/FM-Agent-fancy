# [SPEC]
# Unit: src/languages/erlang.py
#
# ElpClient.__init__(self, proj_dir: str)
#
# Pre-condition:
#   - proj_dir is a non-empty string naming a filesystem path
#
# Post-condition:
#   - The ELP project directory is set to the absolute path of proj_dir
#   - A file:// URI for that project directory is available for use in LSP
#     initialization requests
#   - A positive integer timeout for ELP request operations is configured
#   - An empty, thread-safe message queue exists for receiving JSON-RPC
#     responses from the ELP server
#   - Request identifiers start at 1 and increment atomically across
#     subsequent requests
#   - A thread-safe write lock for the subprocess standard-input stream is
#     initialized and unlocked
#   - The ELP server subprocess and its response reader are not running;
#     the instance is in a pre-connection state
#   - Calling request() or notify() before the context manager has been
#     entered raises an error
#   - Entering the context manager starts the ELP server subprocess in the
#     project directory and begins reading its JSON-RPC responses
# [SPEC]

# [INFO]
# _timeout_seconds() -> int
#   Pre-condition: settings.erlang.timeout_s is a configured integer value
#   Post-condition: returns a positive integer (>= 1) representing the ELP
#     communication timeout in seconds
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
