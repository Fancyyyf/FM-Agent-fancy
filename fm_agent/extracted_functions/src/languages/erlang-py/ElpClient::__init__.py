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
