    def __init__(self, proj_dir):
        self.proj_dir = Path(proj_dir).resolve()
        self.workdir = _locate_workdir(self.proj_dir)
        self.trace_dir = self.workdir / "trace"
        self.events_path = self.trace_dir / "events.jsonl"
        self.opencode_dir = self.trace_dir / "opencode"
        self.bug_dir = self.workdir / "bug_validation"

        # Tail offsets
        self._events_offset = 0
        self._opencode_offsets = {}      # filename → byte offset

        # Aggregates
        self.first_event_time = None
        self.last_event_time = None
        self.stage_counts = defaultdict(lambda: defaultdict(int))   # stage → status → n
        self.stage_active = defaultdict(int)                        # stage → in-flight count (start-end pairs)
        self.totals = defaultdict(int)                              # token bucket → n
        self.cost_native = 0.0
        self.model_seen = None
        self.cache_window = deque(maxlen=CACHE_WINDOW)              # recent (cache_read, total_input) tuples
        self.llm_statuses = deque(maxlen=LLM_STATUS_WINDOW)         # recent LLM call status records
        self.recent_events = deque(maxlen=40)                       # (time, stage, status, summary)
        self.opencode_token_totals = defaultdict(int)               # stage → tokens
        self.opencode_cost = 0.0
        self.opencode_calls = 0
        self._opencode_requests = {}                                # (filename, id) → request metadata

        # Verification verdicts
        self.verification_success = 0
        self.verification_mismatch = 0
        self.verification_error = 0

        # Bug validation
        self.bugs_confirmed = 0
        self.bugs_not_confirmed = 0
        self.bugs_pending = 0     # opencode call done but no result.json yet
