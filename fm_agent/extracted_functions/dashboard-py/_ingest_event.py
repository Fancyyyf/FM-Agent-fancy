# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_ingest_event.py
#
# State._ingest_event(self, ev) -> None
#
# Pre-condition:
#   - ev is a dict parsed from a single JSONL trace event, containing at
#     minimum the string keys "type", "stage", and "status".
#   - ev may optionally contain "start_time" and "end_time" as ISO 8601
#     timestamp strings, "summary" as a string, and "metadata" as a dict.
#   - self is an initialized State with aggregate counters (stage_counts,
#     totals, cost_native, verification_success, verification_mismatch,
#     verification_error), time tracking (first_event_time, last_event_time),
#     a cache-hit-rate window (cache_window), a model tracker (model_seen),
#     and activity histories.
#   - All numeric accumulators are initialized to zero or None (for
#     first/last); defaultdicts are seeded to produce integer counters.
#
# Post-condition:
#   - self.first_event_time and self.last_event_time are updated to the
#     minimum and maximum, respectively, of all valid start_time and
#     end_time values parsed from every ingested event so far.
#   - self.stage_counts[stage][status] is incremented by 1, where stage
#     and status default to "?" when absent from ev.
#   - If ev["type"] == "llm_call":
#       * If ev["metadata"]["model"] is truthy and self.model_seen has not
#         yet been set, self.model_seen is assigned that model value.
#       * If ev["metadata"]["usage"] is a dict containing token counts,
#         the token totals in self.totals for "input", "output",
#         "cache_read", and "cache_write" are increased by the
#         corresponding counts from the usage dict.  Supported usage
#         shapes: Anthropic (input_tokens, output_tokens,
#         cache_read_input_tokens, cache_creation_input_tokens) and
#         OpenAI (prompt_tokens, completion_tokens, with optional
#         prompt_cache_hit_tokens / prompt_cache_miss_tokens for cached
#         token accounting).  If an alternate shape is encountered but
#         no token values are truthy, no totals change.
#       * self.cost_native is increased by the cost computed from the
#         model and usage fields.
#       * When the sum of input tokens plus cache-read and cache-write
#         tokens for this event is positive, the pair
#         (cache_read_tokens_for_this_event,
#         total_input_tokens_for_this_event) is appended to
#         self.cache_window.
#       * self.verification_success is incremented by 1 when
#         ev["status"] == "success" AND
#         ev["metadata"]["purpose"] == "check_post_implies_spec".
#       * self.verification_mismatch is incremented by 1 when
#         ev["status"] == "mismatch".
#       * self.verification_error is incremented by 1 when
#         ev["status"] == "error".
#       * A record is appended to the recent-event history and to the
#         LLM-status history.
#   - If ev["type"] == "opencode_call":
#       * A record is appended to the recent-event history.
#   - For any other value of ev["type"], only the stage_counts increment
#     (from the first bullet) applies.
#   - Missing optional keys in ev (start_time, end_time, metadata, usage,
#     model, purpose) do not cause errors; the corresponding metric
#     updates are simply skipped.
# [SPEC]

# [INFO]
# _parse_iso(timestamp_str) -> Optional[datetime]
#   Pre-condition: timestamp_str is a string or None.
#   Post-condition: Returns a timezone-aware datetime parsed from an
#     ISO 8601 string; returns None when timestamp_str is falsy or
#     cannot be parsed as a valid timestamp.
# [SPLIT]
# _cost_from_usage(model, usage) -> float
#   Pre-condition: model is a string or None; usage is a dict containing
#     token-count fields (input_tokens, output_tokens,
#     cache_read_input_tokens, cache_creation_input_tokens).
#   Post-condition: Returns the monetary cost in USD computed from the
#     model's per-token pricing and the token counts in usage.
#     Returns 0.0 when model is None or pricing data for the model is
#     unavailable.
# [SPLIT]
# State._push_recent(self, ts, stage, status, summary) -> None
#   Pre-condition: ts is a datetime or None; stage, status, and summary
#     are strings.
#   Post-condition: A record containing the given fields is appended to
#     the recent-event history, bounded to a fixed maximum length
#     (oldest entries evicted when at capacity).
# [SPLIT]
# State._push_llm_status(self, ts, source, label, status, model, code, detail) -> None
#   Pre-condition: ts is a datetime or None; source, label, status,
#     model, code, and detail are strings or None.
#   Post-condition: A record containing the given fields is appended to
#     the LLM-status history, bounded to a fixed maximum length
#     (oldest entries evicted when at capacity).
# [SPLIT]
# _llm_code_for_event(status) -> str
#   Pre-condition: status is a string.
#   Post-condition: Returns a non-empty status-code string derived from
#     status; returns an error-type code (e.g., "ERR") when status
#     does not correspond to any known success or mismatch value.
# [INFO]

    def _ingest_event(self, ev):
        et = ev.get("type")
        stage = ev.get("stage", "?")
        status = ev.get("status", "?")
        start = _parse_iso(ev.get("start_time"))
        end = _parse_iso(ev.get("end_time"))
        if start and (self.first_event_time is None or start < self.first_event_time):
            self.first_event_time = start
        if end and (self.last_event_time is None or end > self.last_event_time):
            self.last_event_time = end

        self.stage_counts[stage][status] += 1

        if et == "llm_call":
            md = ev.get("metadata", {})
            model = md.get("model")
            if model and not self.model_seen:
                self.model_seen = model
            usage = md.get("usage") or {}
            if usage:
                # Anthropic-native shape (from new llm_client)
                inp = usage.get("input_tokens", 0) or 0
                out = usage.get("output_tokens", 0) or 0
                cr = usage.get("cache_read_input_tokens", 0) or 0
                cw = usage.get("cache_creation_input_tokens", 0) or 0
                if not any([inp, out, cr, cw]):
                    # OpenAI shape (svip compat path or older runs)
                    inp = usage.get("prompt_tokens", 0) or 0
                    out = usage.get("completion_tokens", 0) or 0
                    # DeepSeek reports cache as flat fields; prompt_tokens is the
                    # TOTAL (hit + miss). Split into disjoint in:new / in:read.
                    hit = usage.get("prompt_cache_hit_tokens")
                    if hit is not None:
                        cr = hit
                        inp = usage.get("prompt_cache_miss_tokens", inp - hit)
                self.totals["input"] += inp
                self.totals["output"] += out
                self.totals["cache_read"] += cr
                self.totals["cache_write"] += cw
                self.cost_native += _cost_from_usage(model, usage)
                total_in = inp + cr + cw
                if total_in > 0:
                    self.cache_window.append((cr, total_in))

            if status == "success" and md.get("purpose") == "check_post_implies_spec":
                self.verification_success += 1
            elif status == "mismatch":
                self.verification_mismatch += 1
            elif status == "error":
                self.verification_error += 1

            summary = ev.get("summary") or md.get("purpose") or "llm_call"
            self._push_recent(end or start, stage, status, summary)
            self._push_llm_status(
                ts=end or start,
                source="direct",
                label=md.get("purpose") or summary,
                status=status,
                model=model,
                code=_llm_code_for_event(status),
                detail=md.get("error"),
            )

        elif et == "opencode_call":
            summary = ev.get("summary") or "opencode_call"
            self._push_recent(end or start, stage, status, summary)
