    def get_call_edges(self, lang_key: str) -> dict:
        """Return {caller_fqn: {callee_fqn, ...}} for the given language.

        Each FQN matches generate_topdown_layers._file_to_fqn for the
        corresponding extracted function (``dir::file-ext::dedup_name``). Edges
        are resolved by codegraph NODE ID (not by bare name), so the precise
        caller/callee identity codegraph computed — which file, which same-named
        sibling — is preserved end-to-end. This lets the call-graph builder use
        the edges directly instead of re-resolving bare names against every
        same-named function (which collapsed siblings and over-approximated
        across files).

        Constructor calls are synthesised from `instantiates` edges: when a
        function instantiates a class, the corresponding constructor method is
        added as a callee.  See _CONSTRUCTOR_FILTER for per-language details.

        NOTE: codegraph itself collapses calls to same-named classes in different
        files onto the first definition (a codegraph resolver limitation for C++,
        not addressable here — see issues/codegraph-samename-class-resolution).
        """
        cg_langs = _CG_LANG.get(lang_key)
        if not cg_langs:
            return {}

        conn = sqlite3.connect(self._db)
        cur = conn.cursor()
        placeholders = ",".join("?" * len(cg_langs))

        # Map every function/method node to its FQN once, using the same per-file
        # dedup as get_functions_by_file, then resolve edges by node id.
        fqn_of = _node_fqn_map(cur, cg_langs)

        result = defaultdict(set)

        # Query 1: regular function/method calls, kept as (source_id, target_id)
        # so each endpoint resolves to its exact node's FQN.
        cur.execute(
            f"""
            SELECT e.source, e.target
            FROM edges e
            JOIN nodes s ON e.source = s.id
            WHERE e.kind = 'calls' AND s.language IN ({placeholders})
            """,
            cg_langs,
        )
        for src_id, tgt_id in cur.fetchall():
            caller, callee = fqn_of.get(src_id), fqn_of.get(tgt_id)
            if caller and callee:
                result[caller].add(callee)

        # Query 2: constructor calls synthesised from instantiates edges.
        # For each `caller instantiates ClassName` edge, find the constructor
        # method inside that class and add it as a synthetic callee.
        ctor_filter = _CONSTRUCTOR_FILTER.get(lang_key)
        if ctor_filter:
            cur.execute(
                f"""
                SELECT e.source, ctor.id
                FROM edges e
                JOIN nodes s   ON e.source = s.id
                JOIN nodes cls ON e.target = cls.id AND cls.kind = 'class'
                JOIN edges ce  ON ce.source = cls.id AND ce.kind = 'contains'
                JOIN nodes ctor ON ce.target = ctor.id
                               AND ctor.kind IN ('method', 'function')
                WHERE e.kind = 'instantiates' AND s.language IN ({placeholders})
                AND {ctor_filter}
                """,
                cg_langs,
            )
            for src_id, ctor_id in cur.fetchall():
                caller, callee = fqn_of.get(src_id), fqn_of.get(ctor_id)
                if caller and callee:
                    result[caller].add(callee)

        conn.close()
        return dict(result)
