"""Probe script for bug: dashboard-py--render_stages
Bug: render_stages() does str(counts.get(key, 0)) without enforcing integer type.
If state.stage_counts contains non-integer values (floats, strings), they are
rendered as-is, violating the spec's requirement of non-negative integer counts.
"""
import sys
import io
from pathlib import Path

# Add repo root to sys.path so `import dashboard` resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from rich.console import Console
    import dashboard
    from dashboard import render_stages

    # Create a State object through the public API
    state = dashboard.State("/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot")

    # Inject a non-integer float into stage_counts
    # This violates the pre-condition, but the spec's post-condition states
    # that counts must be rendered as non-negative integers regardless.
    state.stage_counts["init"]["success"] = 5.5

    # Call the public API
    panel = render_stages(state)

    # Capture rendered output as plain text
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=200, color_system=None)
    console.print(panel)
    rendered = buf.getvalue()

    # Check: if "5.5" appears in output, the bug is confirmed (float leaked through)
    # Expected: should only contain integer representations like "5" or "0"
    if "5.5" in rendered:
        print("CONFIRMED — actual: '5.5' (float) rendered | expected: non-negative integer count")
    else:
        print("NOT CONFIRMED — no non-integer values found in rendered output")
except Exception as e:
    print(f"ERROR: {e.__class__.__name__}: {e}")
    sys.exit(1)
