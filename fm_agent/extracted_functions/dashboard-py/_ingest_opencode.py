# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_ingest_opencode.py
#
# State._ingest_opencode(self, rec, trace_file=None) -> None
#
# Pre-condition:
#   - rec is a dict parsed from a single JSONL line of an OpenCode
#     trace file.  It contains at minimum the key "_kind" (string)
#     and may contain "_id" (call identifier), "_ts" (ISO 8601
#     timestamp), "_trace_file" (string), "model" (string), "usage"
#     (dict), and response status fields.
#   - trace_file is an optional string identifying the source trace
#     file; may be None when the record embeds "_trace_file".
#   - self is an initialized State with OpenCode-specific aggregated
#     metrics: opencode_calls (integer), opencode_token_totals (dict
#     with "input", "output", "cache_read", "cache_write" keys),
#     opencode_cost (float), cache_window (list of (cached, total)
#     pairs), LLM-status history, and an internal request-tracking
#     dictionary _opencode_requests.
#
# Post-condition:
#   - Records with "_kind" == "request" AND a non-None "_id": the
#     request metadata (timestamp, model, URL, purpose) is stored
#     internally keyed by (trace_file, call_id).  No user-visible
#     aggregated metric changes.
#   - Records with "_kind" == "error": an error entry is appended to
#     the LLM-status history.  No token or cost totals change.
#   - Records with "_kind" != "response": no side effects beyond the
#     request and error handling described above.
#   - Records with "_kind" == "response":
#       * If the HTTP status code (from any of "_status", "status",
#         "status_code") is present and not 200, an error entry is
#         appended to the LLM-status history.  No token or cost totals
#         change.
#       * If "usage" is not a dict (missing or non-dict value), a
#         success entry is appended to the LLM-status history.  No
#         token or cost totals change.
#       * If "usage" is a dict but contains no token counts (i.e.,
#         both input and output tokens resolve to zero), a success
#         entry is appended to the LLM-status history.  No token or
#         cost totals change.
#       * Otherwise (usage is a dict with non-zero token counts):
#         - A success entry is appended to the LLM-status history.
#         - self.opencode_calls is incremented by 1.
#         - self.opencode_token_totals["input"],
#           self.opencode_token_totals["output"],
#           self.opencode_token_totals["cache_read"], and
#           self.opencode_token_totals["cache_write"] are increased
#           by the corresponding token counts resolved from the usage
#           dict, supporting both Anthropic-native and OpenAI-compat
#           shapes (with DeepSeek cache-hit/miss splitting for the
#           OpenAI compat path).
#         - self.opencode_cost is increased by the cost computed from
#           the model and resolved usage.
#         - If total input tokens (input + cache_read + cache_write)
#           for this response are positive, the pair
#           (cache_read_tokens, total_input_tokens) is appended to
#           self.cache_window.
#   - Missing optional fields (keys absent or None) do not cause
#     errors; the corresponding metric updates or status entries are
#     simply skipped.
#   - The strip-started normalization is applied transparently so
#     that records from streaming-delta key formats and plain-key
#     formats are handled identically.
# [SPEC]

# [INFO]
# _strip_star(d) -> dict
#   Pre-condition: d is a dict.
#   Post-condition: Returns a new dict where every key that starts
#     with "*" has that prefix removed.  Keys without the prefix are
#     unchanged.  The returned dict has the same values as d for
#     each (possibly renamed) key.
# [SPLIT]
# _parse_iso(timestamp_str) -> Optional[datetime]
#   Pre-condition: timestamp_str is a string or None.
#   Post-condition: Returns a timezone-aware datetime parsed from an
#     ISO 8601 string; returns None when timestamp_str is falsy or
#     cannot be parsed as a valid timestamp.
# [SPLIT]
# _trace_value(d, *keys) -> Optional[str]
#   Pre-condition: d is a dict; keys is a sequence of string key
#     names.
#   Post-condition: Returns the value associated with the first key
#     in keys that exists in d and has a truthy value.  Returns None
#     if no key in keys maps to a truthy value in d.
# [SPLIT]
# State._push_llm_status(self, ts, source, label, status, model, code, detail) -> None
#   Pre-condition: ts is a datetime or None; source, label, status,
#     model, code, and detail are strings or None.
#   Post-condition: A record containing the given fields is appended
#     to the LLM-status history, bounded to a fixed maximum length
#     (oldest entries evicted when at capacity).
# [SPLIT]
# _cost_from_usage(model, usage) -> float
#   Pre-condition: model is a string or None; usage is a dict containing
#     token-count fields.
#   Post-condition: Returns the monetary cost in USD computed from the
#     model's per-token pricing and the token counts in usage.
#     Returns 0.0 when model is None or pricing data for the model is
#     unavailable.
# [SPLIT]
# _get_nested(d, *keys) -> Optional[Any]
#   Pre-condition: d is a dict; keys is a sequence of string key
#     names.
#   Post-condition: Returns the value at d[k1][k2]...[kN] for the
#     given key chain, where each intermediate value must be a dict.
#     Returns None when any intermediate key is missing or the
#     corresponding value is not a dict.
# [INFO]

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
