    def __enter__(self):
        self._proc = subprocess.Popen(
            _elp_argv(),
            cwd=self.proj_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self._reader = _JsonRpcReader(self._proc.stdout, self._messages)
        self._reader.start()
        return self
