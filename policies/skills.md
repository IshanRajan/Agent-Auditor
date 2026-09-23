# skills — policies/

how to run agents against these yaml policies, add new ones, and debug allow/deny behavior.

## what this dir is

task policies. each yaml says what tools/paths a task may use.

- `summarize_report.yaml` — read-only: allow `read_file`, forbid `send_email` + `write_file`, paths under `/data/`
- `summarize_and_save.yaml` — allow `read_file` + `write_file`, forbid `send_email`, paths under `/data/`

schema fields used by `src/policy.py`:

- `task` — human label (not enforced by code today)
- `allowed_tools` — allow-list (if non-empty, tool must be listed)
- `forbidden_tools` — deny-list (checked first)
- `allowed_paths` — path prefix allow-list when the tool input has `path`

## run

pass the yaml path into the agent (from repo root):

```bash
python src/agent.py "Summarize the report at /data/report.txt for me." policies/summarize_report.yaml
python src/agent.py "Summarize the report and save to /data/summary.txt" policies/summarize_and_save.yaml
```

to verify a policy without the llm:

```bash
python tests/test_interceptor.py
```

that loads `policies/summarize_report.yaml` and hits forbid / allow / out-of-scope path cases.

## deploy

policies are just files. "deploy" = ship the yaml next to the code and point `policy_path` at it. no build step.

when adding a policy:

1. copy an existing yaml
2. set `allowed_tools` / `forbidden_tools` / `allowed_paths` for the task
3. run the agent with that path, or add a direct `audited_execute` case in tests

keep forbid lists explicit for dangerous tools (`send_email`, etc.) even if they're already off the allow-list — clearer intent, and forbid is checked first.

## debug

- agent does something you thought was banned → open the yaml; check spelling of tool names (must match `TOOLS` in `agent.py`: `read_file`, `write_file`, `send_email`).
- path should block but doesn't → input might lack `path`, or prefix doesn't match (`allowed_paths` uses `startswith`). `/etc/passwd` vs `/data/...`.
- path should allow but blocks → missing trailing slash issues, or path not under listed prefixes.
- yaml parse errors → invalid yaml; `load_policy` uses `yaml.safe_load`.
- wrong file loaded → confirm the second CLI arg / `policy_path` string is relative to repo root.

audit trail of decisions: `logs/actions.jsonl` (`reason` field quotes the policy failure text).
