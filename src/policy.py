"""
Policy loading and enforcement logic.

A policy is just a YAML file describing what a given task is allowed
to do: which tools it can call, which tools are explicitly forbidden,
and which paths it can touch. check_action() is the single function
the interceptor calls before letting any tool run.
"""

import yaml


class PolicyViolation:
    """Represents a single check result. `allowed` tells the caller
    whether to let the action through; `reason` is human-readable."""

    def __init__(self, allowed: bool, reason: str):
        self.allowed = allowed
        self.reason = reason

    def __repr__(self):
        status = "ALLOWED" if self.allowed else "BLOCKED"
        return f"<{status}: {self.reason}>"


def load_policy(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def check_action(tool_name: str, tool_input: dict, policy: dict) -> PolicyViolation:
    """Check a single proposed tool call against a policy. Order of
    checks matters: forbidden_tools is checked first since it's an
    explicit deny regardless of anything else."""

    forbidden = policy.get("forbidden_tools", [])
    if tool_name in forbidden:
        return PolicyViolation(False, f"tool '{tool_name}' is explicitly forbidden")

    allowed = policy.get("allowed_tools", [])
    if allowed and tool_name not in allowed:
        return PolicyViolation(False, f"tool '{tool_name}' is not in allowed_tools")

    # Path scoping: only applies if the tool call has a 'path' argument
    # and the policy defines allowed_paths.
    allowed_paths = policy.get("allowed_paths")
    if allowed_paths and "path" in tool_input:
        path = tool_input["path"]
        if not any(path.startswith(prefix) for prefix in allowed_paths):
            return PolicyViolation(
                False, f"path '{path}' is outside allowed_paths {allowed_paths}"
            )

    return PolicyViolation(True, "action complies with policy")