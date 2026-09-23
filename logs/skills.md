# skills — logs/

how to read, use, and debug audit logs. nothing here is "run" as code.

## what this dir is

append-only jsonl audit trails written by `src/interceptor.py`.

- `actions.jsonl` — agent runs (`audited_execute` default `log_path`)
- `test_actions.jsonl` — interceptor tests (`log_path="logs/test_actions.jsonl"`)

each line is one json object:

```json
{"timestamp": 0.0, "tool": "read_file", "input": {"path": "/data/report.txt"}, "allowed": true, "reason": "action complies with policy", "result": "..."}
```

## run

you don't run this directory. generate logs by running the agent or tests from repo root:

```bash
python src/agent.py
python tests/test_interceptor.py
```

then inspect:

```bash
# last few decisions (powershell)
Get-Content logs/actions.jsonl -Tail 20

# or pretty-print one line with python
python -c "import json; print(json.dumps(json.loads(open('logs/actions.jsonl').read().splitlines()[-1]), indent=2))"
```

## deploy

logs are local runtime output. don't treat them as an app to deploy.

- directory is auto-created by the interceptor if missing.
- usually keep `*.jsonl` out of releases; fine to gitignore if they get noisy (they're currently present as demo/evidence).
- never put secrets into tool inputs you care about logging — `input` and `result` are written in full.

## debug

- empty file / missing file → no tool calls hit `audited_execute` yet, wrong `log_path`, or cwd wasn't root when the process started (relative `logs/...`).
- `allowed: true` but you expected a block → fix the policy yaml or `check_action`, not the log format.
- `allowed: false` with `result` starting `BLOCKED by policy:` → interceptor worked; agent saw the block string as the tool result.
- duplicate / many lines → normal; files append. truncate when investigating a single run.
- corrupt last line → process killed mid-write; drop the bad line or clear the file.
