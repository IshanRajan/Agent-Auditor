"""
Interceptor: the layer that sits between "the agent decided to call a
tool" and "the tool actually ran". Every call goes through here first.
"""

import json
import os
import time

from policy import check_action


def audited_execute(tool_name: str, tool_input: dict, policy: dict,
                     real_execute_fn, log_path: str = "logs/actions.jsonl") -> str:
    """Check a proposed tool call against policy, log the decision,
    and only run it if allowed. Returns the string result the agent
    sees (either the real tool output or a block message)."""

    check = check_action(tool_name, tool_input, policy)

    if check.allowed:
        result = real_execute_fn(tool_name, tool_input)
    else:
        result = f"BLOCKED by policy: {check.reason}"

    _log_action(tool_name, tool_input, check, result, log_path)
    return result


def _log_action(tool_name, tool_input, check, result, log_path):
    entry = {
        "timestamp": time.time(),
        "tool": tool_name,
        "input": tool_input,
        "allowed": check.allowed,
        "reason": check.reason,
        "result": result,
    }

    log_dir = os.path.dirname(log_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    status = "ALLOWED" if check.allowed else "BLOCKED"
    print(f"[audit] {status} — {tool_name}({tool_input}) — {check.reason}")