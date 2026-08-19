    def scan_bugs(self):
        self.bugs_confirmed = 0
        self.bugs_not_confirmed = 0
        if not self.bug_dir.exists():
            return
        for path in self.bug_dir.glob("*.result.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    d = json.load(f)
            except Exception:
                continue
            status = (d.get("confirmation_status") or "").lower()
            if "not" in status:
                self.bugs_not_confirmed += 1
            elif "confirm" in status:
                self.bugs_confirmed += 1
            else:
                self.bugs_not_confirmed += 1  # treat unknown as not confirmed
        # pending = bug_validation opencode_calls with success status, minus results files
        bv = self.stage_counts.get("bug_validation", {})
        bv_done = sum(bv.values())
        self.bugs_pending = max(0, bv_done - (self.bugs_confirmed + self.bugs_not_confirmed))
