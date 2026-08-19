    def _record(rel_path, score):
        if rel_path not in scored or score > scored[rel_path]:
            scored[rel_path] = score
