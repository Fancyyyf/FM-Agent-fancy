# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/__init__.py
#
# State.__init__(self, proj_dir: str | Path)
#
# Pre-condition:
#   - proj_dir is a string or Path-like value referencing an existing directory
#     on the filesystem
#
# Post-condition:
#   - self.proj_dir is the fully-resolved absolute Path of proj_dir
#   - self.workdir is the Path to the fm_agent/ workspace directory located
#     relative to the resolved project directory
#   - self.trace_dir, self.events_path, self.opencode_dir, and self.bug_dir are
#     sub-Paths of self.workdir referencing the trace output directory, the
#     events JSONL file, the raw OpenCode trace directory, and the bug
#     validation output directory respectively
#   - All numeric aggregation counters and monetary totals are initialized
#     to zero or zero-valued floats
#   - All scalar references (first_event_time, last_event_time, model_seen)
#     are initialized to None
#   - All bounded deques (cache_window, llm_statuses, recent_events) are
#     initialized as empty collections with their configured maximum lengths
#   - The _opencode_requests dictionary and _opencode_offsets dictionary are
#     initialized as empty mappings
#   - The State instance is ready to ingest incremental trace events via
#     subsequent refresh operations without requiring further initialization
# [SPEC]

# [INFO]
# _locate_workdir(proj_dir: Path) -> Path
#   Pre-condition: proj_dir is a resolved absolute Path to an existing directory
#   Post-condition: Returns the Path to the fm_agent/ workspace directory;
#     when proj_dir itself is an fm_agent/ workspace it returns proj_dir;
#     otherwise returns the fm_agent/ subdirectory within proj_dir
# [INFO]

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
