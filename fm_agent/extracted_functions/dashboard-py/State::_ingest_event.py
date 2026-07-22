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
