    def _push_llm_status(self, ts, source, label, status, model=None, code=None, detail=None):
        when = ts.strftime("%H:%M:%S") if ts else ""
        self.llm_statuses.append(
            {
                "time": when,
                "source": source,
                "label": label or "llm_call",
                "status": status or "?",
                "model": model,
                "code": code or status or "?",
                "detail": detail,
            }
        )
