    def close(self):
        proc = self._proc
        if proc is None:
            return
        try:
            if proc.poll() is None:
                try:
                    self.request("shutdown")
                except Exception:
                    pass
                try:
                    self.notify("exit")
                except Exception:
                    pass
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
        finally:
            for stream in (proc.stdin, proc.stdout):
                if stream:
                    try:
                        stream.close()
                    except OSError:
                        pass
            self._proc = None
