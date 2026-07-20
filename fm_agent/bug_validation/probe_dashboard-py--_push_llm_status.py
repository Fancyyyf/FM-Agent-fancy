"""Probe script for _push_llm_status bug validation.

Bug: The _push_llm_status method allegedly only evicts when len(old) == capacity
but not when len(old) > capacity, potentially exceeding the max length.
Using Python's collections.deque with maxlen, we test whether exceeding
the capacity boundary is actually possible.
"""
import sys
import os
from datetime import datetime
from collections import deque

# Script is at fm_agent/bug_validation/probe_*.py; repo root is 3 levels up
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    from dashboard import State

    LLM_STATUS_WINDOW = 80  # from dashboard.py

    repo_root = REPO_ROOT
    state = State(repo_root)
    ts = datetime(2025, 1, 15, 12, 30, 45)

    # Fill to exactly capacity
    state.llm_statuses.clear()
    for i in range(LLM_STATUS_WINDOW):
        state._push_llm_status(ts, "test", f"label{i}", "success", model="test-model")

    assert len(state.llm_statuses) == LLM_STATUS_WINDOW, \
        f"Expected {LLM_STATUS_WINDOW} entries at capacity, got {len(state.llm_statuses)}"

    # Push one more — should stay at capacity (oldest evicted by deque)
    first_entry_label = state.llm_statuses[0]["label"]
    state._push_llm_status(ts, "test", "overflow", "success", model="test-model")

    len_after = len(state.llm_statuses)
    new_first_label = state.llm_statuses[0]["label"]

    if len_after > LLM_STATUS_WINDOW:
        print(f'CONFIRMED — capacity exceeded: len={len_after} > {LLM_STATUS_WINDOW}')
        sys.exit(0)

    # Check eviction: oldest should be gone
    if first_entry_label == new_first_label:
        print(f'CONFIRMED — oldest entry not evicted when at capacity (label: {new_first_label})')
        sys.exit(0)

    # Test: append more items than maxlen directly to the deque
    state.llm_statuses.clear()
    for i in range(LLM_STATUS_WINDOW + 10):
        state.llm_statuses.append(
            {"time": "12:00:00", "source": "test", "label": f"l{i}",
             "status": "success", "model": "m", "code": "200", "detail": None}
        )

    if len(state.llm_statuses) > LLM_STATUS_WINDOW:
        print(f'CONFIRMED — deque append did not evict excess: len={len(state.llm_statuses)} > {LLM_STATUS_WINDOW}')
        sys.exit(0)

    # Final test: push via _push_llm_status on an already-full deque
    state.llm_statuses.clear()
    for i in range(LLM_STATUS_WINDOW):
        state._push_llm_status(ts, "test", f"label{i}", "success", model="test-model")

    state._push_llm_status(ts, "test", "final", "success", model="test-model")
    if len(state.llm_statuses) > LLM_STATUS_WINDOW:
        print(f'CONFIRMED — _push_llm_status exceeded capacity: len={len(state.llm_statuses)} > {LLM_STATUS_WINDOW}')
        sys.exit(0)

    # All checks passed
    print(f'NOT CONFIRMED — deque maxlen={LLM_STATUS_WINDOW} correctly enforces capacity limit. '
          f'oldest evicted (was "{first_entry_label}", now "{new_first_label}"), '
          f'final len={len(state.llm_statuses)}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
