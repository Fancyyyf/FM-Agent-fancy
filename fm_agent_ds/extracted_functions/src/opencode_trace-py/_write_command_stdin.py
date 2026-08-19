def _write_command_stdin(stream, text):
    try:
        stream.write(text)
        stream.flush()
    finally:
        stream.close()
