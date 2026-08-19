def _setup_incremental_logging(work_dir):
    """
    Route the incremental pipeline's progress output to a log file AND stdout.

    Configures the root logger with a FileHandler at
    work_dir/incremental_<YYYYmmdd_HHMMSS>.log (the timestamp is taken when this is called,
    so each pipeline run writes its own log file rather than overwriting the previous one) so
    every logging.* call in this module — the stage-by-stage progress that used to be
    print()ed, plus the existing warning/error/exception records — is preserved on disk. A
    second StreamHandler mirrors the same records to stdout, so callers that capture the
    subprocess output (e.g. the benchmark runner, which greps stdout for the final
    "confirmed bugs in N function(s)" marker) can see the result without reading the log
    file. The log file is wiped by the runner's per-trial revert, so stdout is the only
    place the result reliably survives. Any handlers a previous call (or import) installed
    are replaced, so invoking the pipeline repeatedly in one process does not duplicate log
    lines.

    Additionally, sys.stdout is wrapped in an _StdoutTee so the bare print() progress
    emitted by the shared helpers this pipeline calls (run_extraction's verbose output,
    generate_topdown_layers, rank_functions_in_file, and _run_setup_extract's retry/error
    messages) is mirrored into the same log file rather than only reaching the console. The
    console StreamHandler is bound to the underlying console stream (not the tee), so
    logging.* records are written to the file exactly once. Returns the absolute path of the
    log file.
    """
    os.makedirs(work_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(work_dir, f"incremental_{timestamp}.log")

    # If a previous call already wrapped stdout, unwrap to the real console stream first so
    # repeated invocations don't stack tees (each adding another copy of every print()).
    console_stream = getattr(sys.stdout, "_console", sys.stdout)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    # Bind the console handler to the real console stream, NOT the tee below, so logging.*
    # records land in the file once (via file_handler) instead of twice (file_handler + tee).
    console_handler = logging.StreamHandler(console_stream)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Replace existing handlers so repeated calls don't duplicate lines, then log to both
    # the per-run file and stdout.
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # Mirror bare print() output (from the shared helpers above) into the same log file.
    sys.stdout = _StdoutTee(console_stream, file_handler.stream)
    return log_path
