    def _ingest_opencode(self, rec, trace_file=None):
        # opencode-trace alternates request and response; usage lives on responses.
        # The @lucentia plugin prefixes streaming-delta keys with "*" (e.g. "*usage",
        # "*input_tokens"). Older runs used plain names. Strip the prefix so both work.
        rec = _strip_star(rec)
        kind = rec.get("_kind")
        call_id = rec.get("_id")
        trace_key = rec.get("_trace_file") or trace_file
        if kind == "request" and call_id is not None:
            self._opencode_requests[(trace_key, call_id)] = {
                "ts": _parse_iso(rec.get("_ts")),
                "model": rec.get("model"),
                "url": rec.get("_url"),
                "purpose": rec.get("_purpose"),
            }
            return
        if kind == "error":
            req = self._opencode_requests.get((trace_key, call_id), {})
            self._push_llm_status(
                ts=_parse_iso(rec.get("_ts")) or req.get("ts"),
                source="opencode",
                label=req.get("purpose") or rec.get("_purpose") or rec.get("_url") or "opencode",
                status="error",
                model=rec.get("model") or req.get("model"),
                code=_trace_value(rec, "_status", "status", "status_code") or "ERR",
                detail=_trace_value(rec, "_error", "error", "message"),
            )
            return
        if kind != "response":
            return
        req = self._opencode_requests.get((trace_key, call_id), {})
        status_code = _trace_value(rec, "_status", "status", "status_code")
        if status_code and str(status_code) != "200":
            self._push_llm_status(
                ts=_parse_iso(rec.get("_ts")) or req.get("ts"),
                source="opencode",
                label=req.get("purpose") or rec.get("_purpose") or rec.get("_url") or "opencode",
                status="error",
                model=rec.get("model") or req.get("model"),
                code=status_code,
                detail=_trace_value(rec, "_error", "error", "message"),
            )
            return
        usage = rec.get("usage")
        if not isinstance(usage, dict):
            self._push_llm_status(
                ts=_parse_iso(rec.get("_ts")) or req.get("ts"),
                source="opencode",
                label=req.get("purpose") or rec.get("_purpose") or "opencode",
                status="success",
                model=rec.get("model") or req.get("model"),
                code="200",
            )
            return
        usage = _strip_star(usage)
        inp = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
        out = usage.get("output_tokens") or usage.get("completion_tokens") or 0
        if not (inp or out):
            self._push_llm_status(
                ts=_parse_iso(rec.get("_ts")) or req.get("ts"),
                source="opencode",
                label=req.get("purpose") or rec.get("_purpose") or "opencode",
                status="success",
                model=rec.get("model") or req.get("model"),
                code="200",
            )
            return  # not a response payload
        self._push_llm_status(
            ts=_parse_iso(rec.get("_ts")) or req.get("ts"),
            source="opencode",
            label=req.get("purpose") or rec.get("_purpose") or "opencode",
            status="success",
            model=rec.get("model") or req.get("model"),
            code="200",
        )
        self.opencode_calls += 1
        # DeepSeek (openai-compat) reports cache as flat top-level fields, and
        # prompt_tokens is the TOTAL (hit + miss). Split it into the disjoint
        # in:new / in:read the rest of the dashboard assumes — otherwise the
        # cached half is double-counted and the hit rate reads low.
        hit = usage.get("prompt_cache_hit_tokens")
        if hit is not None:
            cr = hit
            inp = usage.get("prompt_cache_miss_tokens", inp - hit)
        else:
            cr = (usage.get("cache_read_input_tokens")
                  or _get_nested(usage, "prompt_tokens_details", "cached_tokens")
                  or _get_nested(usage, "input_tokens_details", "cached_tokens")
                  or 0)
        cw = (usage.get("cache_creation_input_tokens")
              or usage.get("claude_cache_creation_5_m_tokens")
              or 0)
        self.opencode_token_totals["input"] += inp
        self.opencode_token_totals["output"] += out
        self.opencode_token_totals["cache_read"] += cr
        self.opencode_token_totals["cache_write"] += cw
        model = rec.get("model")
        self.opencode_cost += _cost_from_usage(model, {
            "input_tokens": inp, "output_tokens": out,
            "cache_read_input_tokens": cr, "cache_creation_input_tokens": cw,
        })
        total_in = inp + cr + cw
        if total_in > 0:
            self.cache_window.append((cr, total_in))
