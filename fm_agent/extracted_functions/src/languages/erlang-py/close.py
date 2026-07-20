# [SPEC]
# Unit: fm_agent/extracted_functions/src/languages/erlang-py/close.py
#
# close(self) -> None
#
# Pre-condition:
#   - self._proc is either None or a subprocess.Popen instance that may be running or already terminated
#
# Post-condition:
#   - If self._proc was None on entry, the method returns immediately with no observable side effects
#   - If self._proc was a running process, it is no longer executing after the method returns
#   - The subprocess is first asked to shut down gracefully; if it does not exit within a bounded interval, it is forcibly terminated; if it still does not exit after a second bounded interval, it is forcibly killed
#   - All I/O streams connected to the subprocess (stdin and stdout) are closed before the method returns, regardless of whether individual shutdown or stream-close operations succeed or fail
#   - self._proc is set to None
#   - No exception raised during any shutdown or cleanup step propagates to the caller
# [SPEC]

# [INFO]
# self.request(method: str) -> Any
#   Pre-condition: self has an active pipe connection to the subprocess stdin
#   Post-condition: Sends a JSON-RPC request with the given method name to the subprocess via stdin; raises an exception if the pipe is broken or closed
# [SPLIT]
# self.notify(method: str) -> None
#   Pre-condition: self has an active pipe connection to the subprocess stdin
#   Post-condition: Sends a JSON-RPC notification with the given method name to the subprocess via stdin; raises an exception if the pipe is broken or closed
# [INFO]

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
