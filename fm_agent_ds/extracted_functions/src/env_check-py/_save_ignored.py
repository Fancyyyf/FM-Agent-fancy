def _save_ignored(work_dir, ignored):
    path = _memory_path(work_dir)
    with open(path, "w") as f:
        for item in sorted(ignored):
            f.write(item + "\n")
