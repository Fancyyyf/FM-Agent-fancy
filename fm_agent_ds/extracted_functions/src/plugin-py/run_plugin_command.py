def run_plugin_command(
    cmd: str, plugin_root: Path, proj_dir: str, label: str = ""
) -> None:
    """Execute a plugin bash command with ``check=True`` so failure stops the pipeline.

    Relative file paths in *cmd* are resolved under *plugin_root*. The command runs
    in *proj_dir* with ``FM_AGENT_PLUGIN_ROOT`` set to the plugin root.
    """
    resolved = _resolve_command(cmd, plugin_root)
    env = dict(os.environ, FM_AGENT_PLUGIN_ROOT=str(plugin_root))
    try:
        subprocess.run(resolved, shell=True, check=True, cwd=proj_dir, env=env)
    except subprocess.CalledProcessError as e:
        label_prefix = f"Plugin {label}: " if label else ""
        print(
            f"[Pipeline] ERROR: {label_prefix}command exited with code {e.returncode}: "
            f"{resolved}"
        )
        raise
