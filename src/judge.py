"""
LLM-judge: verifies whether the agent's final output actually
satisfied the task, given what it did along the way.

This is a different check than the interceptor. The interceptor asks
"was each individual tool call allowed?" The judge asks "did the whole
run actually accomplish what was asked, correctly?" An agent can pass
every policy check and still do a bad job — wrong summary, missed part
of the task, made something up. This catches that.
"""

import json

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

JUDGE_MODEL = "claude-sonnet-4-6"

JUDGE_SYSTEM = """You are a strict verifier reviewing whether an AI agent \
actually completed the task it was given, based on its full transcript \
of tool calls and final response.

Judge only what's in the transcript — don't assume good faith, don't \
fill in gaps. Check for:
- Did it complete every part of the task, not just part of it?
- Is the final answer actually supported by the tool results it saw, \
or did it make something up?
- Did it do anything outside the scope of what was asked?

Respond with ONLY a JSON object, no other text:
{"verdict": "pass" or "fail", "reason": "one sentence explaining why"}"""


def judge_run(task: str, transcript_summary: str) -> dict:
    """Ask a separate Claude call to verify a completed agent run.
    transcript_summary should be a compact text description of what
    happened — task, each tool call + result, and the final answer."""

    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=300,
        system=JUDGE_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"TASK GIVEN TO AGENT:\n{task}\n\n"
                    f"TRANSCRIPT:\n{transcript_summary}"
                ),
            }
        ],
    )

    raw = response.content[0].text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"verdict": "error", "reason": f"judge returned non-JSON: {raw}"}


def summarize_transcript(task: str, history: list) -> str:
    """Turn the raw message history from run_agent() into a compact
    text summary the judge can read — each tool call, what it actually
    returned, and the agent's final text response. Including the real
    tool results (not just the agent's claims about them) is what lets
    the judge catch fabricated or unsupported answers."""
    lines = []
    for msg in history:
        content = msg["content"]
        if not isinstance(content, list):
            continue

        if msg["role"] == "assistant":
            for block in content:
                if getattr(block, "type", None) == "tool_use":
                    lines.append(f"CALLED: {block.name}({json.dumps(block.input)})")
                elif getattr(block, "type", None) == "text":
                    lines.append(f"SAID: {block.text}")

        elif msg["role"] == "user":
            for block in content:
                # tool_result entries are plain dicts we built ourselves
                # in agent.py, not SDK objects, so use dict access.
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    lines.append(f"RESULT: {block['content']}")

    return "\n".join(lines)