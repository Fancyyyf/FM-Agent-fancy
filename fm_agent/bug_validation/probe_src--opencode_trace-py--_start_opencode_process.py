"""Probe script for bug src--opencode_trace-py--_start_opencode_process.

Bug: When stdin_text is None, code passes stdin=None to subprocess.Popen,
which causes the child to inherit the parent's stdin. The spec requires
stdin to NOT be connected (should be subprocess.DEVNULL).

If the parent's stdin is already /dev/null, the bug is masked (child
inherits /dev/null, which looks correct). To reliably demonstrate the
bug, we temporarily replace the parent's stdin fd with a pipe before
calling the function.
"""

import os
import sys
import tempfile
import time


def main():
    work_dir = tempfile.mkdtemp(prefix="probe_opencode_")
    proj_dir = work_dir
    result_file = os.path.join(work_dir, "stdin_result.txt")

    # Write a small check script to disk
    check_script = os.path.join(work_dir, "check_stdin.py")
    with open(check_script, "w") as f:
        f.write("""import os
result_file = os.environ.get('PROBE_RESULT_FILE', '')
try:
    link = os.readlink('/proc/self/fd/0')
    result = 'CONNECTED' if link != '/dev/null' else 'DEVNULL'
except Exception as e:
    result = 'ERROR:' + str(e)
with open(result_file, 'w') as f:
    f.write(result)
""")

    try:
        # Add repo root to path and import
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from src.opencode_trace import start_opencode_traced

        os.environ["PROBE_RESULT_FILE"] = result_file

        # Replace parent's stdin (fd 0) with a pipe so the child inherits
        # a real connection instead of /dev/null.
        orig_stdin_fd = os.dup(0)       # save original
        pipe_r, pipe_w = os.pipe()       # create a pipe
        os.dup2(pipe_r, 0)              # replace fd 0 with pipe read end
        os.close(pipe_r)                # close the extra fd

        try:
            # Plain list -> command_stdin returns None -> stdin_text is None
            # -> buggy stdin=None is used -> child inherits the pipe
            record = start_opencode_traced(
                proj_dir=proj_dir,
                work_dir=work_dir,
                command=["python3", check_script],
                stage="probe_test",
            )

            exit_code = record.proc.wait(timeout=10)

            if record.log_thread:
                record.log_thread.join(timeout=5)

            actual = "NO_RESULT_FILE"
            for _ in range(20):
                if os.path.exists(result_file):
                    with open(result_file, "r") as f:
                        actual = f.read().strip()
                    break
                time.sleep(0.1)

        finally:
            # Restore original stdin
            os.dup2(orig_stdin_fd, 0)
            os.close(orig_stdin_fd)
            os.close(pipe_w)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    expected = "DEVNULL"
    if actual.startswith("CONNECTED"):
        print(f"CONFIRMED - bug reproduced: stdin inherited from parent pipe (actual: {actual}), expected: {expected}")
    elif actual == "DEVNULL":
        print(f"NOT CONFIRMED - stdin is /dev/null as expected (actual: {actual})")
    elif actual.startswith("ERROR"):
        print(f"ERROR - stdin check failed in child: {actual}")
        sys.exit(1)
    else:
        print(f"NOT CONFIRMED - unexpected result: {actual}")


if __name__ == "__main__":
    main()
