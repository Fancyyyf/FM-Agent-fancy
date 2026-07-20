# [SPEC]
# Unit: fm_agent/extracted_functions/src/languages/erlang-py/__enter__.py
#
# __enter__(self) -> ElpClient
#
# Pre-condition:
#   - self.proj_dir is a path to an existing directory
#   - _elp_argv() returns a non-empty sequence of strings usable as a subprocess argument vector
#
# Post-condition:
#   - A child process running the Erlang Language Platform (ELP) binary is started with
#     working directory self.proj_dir, its stdin and stdout connected as pipes, and its
#     stderr discarded
#   - self._proc references the running Popen instance for the ELP subprocess
#   - A background daemon reader is active that reads lines from the ELP subprocess stdout,
#     deserializes each line as a JSON-RPC message object, and appends those objects to
#     self._messages (which is initially empty)
#   - Returns self
# [SPEC]

# [INFO]
# subprocess.Popen(args, *, cwd=None, stdin=None, stdout=None, stderr=None) -> subprocess.Popen
#   Pre-condition: args is a sequence of program arguments; cwd if given is a valid directory
#   Post-condition: Executes the given program in a new child process and returns a Popen
#     instance whose stdin, stdout, and stderr handles are connected as specified
# [SPLIT]
# _JsonRpcReader(stream, messages) -> _JsonRpcReader
#   Pre-condition: stream is a readable binary stream providing newline-delimited JSON-RPC
#     messages; messages is a thread-safe queue.Queue
#   Post-condition: Returns a configured daemon Thread instance ready to read from stream
# [SPLIT]
# _JsonRpcReader.start() -> None
#   Pre-condition: The reader's stream is open and readable
#   Post-condition: A background thread begins reading lines from stream, deserializing each
#     as a JSON-RPC message object, and enqueuing each object into messages
# [INFO]

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
