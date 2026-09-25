# master skills — Agent-Auditor

project-wide agent guide: what this is, how it runs, and how the pieces fit together.

**this file is self-improving.** agents must update it when they learn something real about the project (see [self-improve protocol](#self-improve-protocol) and [findings log](#findings-log)).

per-directory details live in:
- `src/skills.md`
- `policies/skills.md`
- `tests/skills.md`
- `logs/skills.md`

---

## self-improve protocol

**standing rule for every agent working in this repo:** after you make a finding or fix a critical bug, update **this** file (`skills.md` at the repo root) in the same turn — do not wait to be asked.

### when to update (mandatory)

| trigger | what to do |
|---------|------------|
| **finding** — surprising behavior, injection result, policy gap, model quirk, "works but only if…" | append to [findings log](#findings-log); patch architecture/run/debug if the mental model changed |
| **critical bug fix** — wrong allow/deny, crash on happy path, auth/path/cwd footgun, broken audit log, test lying about pass | append to findings log with root cause + fix; update debug table and any wrong run/architecture text |
| **new run path / CLI / policy / test** | update [how to run](#how-to-run) / [layout](#layout) / architecture so the next agent can reproduce |
| **debug tip that took real time to discover** | add a row to [debug (quick)](#debug-quick) |

### when not to spam it

skip for typos, renames with no behavior change, or drive-by formatting. if unsure: **finding or critical fix → write it down.**

### how to write an entry

newest first under [findings log](#findings-log). keep it short:

```markdown
### YYYY-MM-DD — short title
- **type:** finding | critical-fix
- **what:** one or two sentences
- **why it matters:** what breaks / what we learned
- **fix or follow-up:** what changed in code (if any), or what still needs proving
```

also fix any stale section in this file that the finding made wrong (architecture diagram, CLI, trust boundary, debug table). if the detail is directory-specific, update that dir's `skills.md` too — but the **master** log entry is required either way.

### done checklist (agent)

- [ ] finding or critical fix happened this turn
- [ ] findings log entry added (newest first)
- [ ] run / architecture / debug sections still accurate
- [ ] per-dir `skills.md` touched only if that dir's runbook changed

---

## what this project is

Agent-Auditor is a **policy audit layer** plus an **outcome judge** for a tool-calling LLM agent. the model can propose tool calls; before any tool actually runs, an interceptor checks the call against a yaml policy (allowed tools, forbidden tools, allowed path prefixes) and logs the decision. after the run, a separate judge reviews the full transcript and checks whether the task was actually completed.

the agent does not know it's audited. stubs fake the filesystem and email so you can demo prompt-injection safely without real side effects.

---

## architecture

```
user task + policy yaml
        │
        ▼
┌───────────────────┐
│  src/agent.py     │  Anthropic tool-calling loop
│  TOOLS + FAKE_FS  │  proposes tool_use blocks
└─────────┬─────────┘
          │ every tool call
          ▼
┌───────────────────┐
│ src/interceptor.py│  audited_execute()
│  allow → run tool │  deny → return "BLOCKED by policy: ..."
│  always append    │  → logs/*.jsonl + [audit] on stdout
└─────────┬─────────┘
          │ uses
          ▼
┌───────────────────┐
│  src/policy.py    │  load_policy() + check_action()
│  forbidden first  │  then allow-list, then path prefixes
└───────────────────┘
          ▲
          │ loaded from
┌───────────────────┐
│  policies/*.yaml  │  per-task allow/forbid/path rules
└───────────────────┘

after the loop finishes:
┌───────────────────┐
│  src/judge.py     │  summarize_transcript() must include RESULT lines
│  judge_run()      │  separate Claude call → {"verdict","reason"}
└───────────────────┘
```

### components

| piece | role |
|-------|------|
| `src/agent.py` | CLI + loop. talks to Claude, defines tools, owns `FAKE_FS` / `execute_tool`, calls `audited_execute` for each tool use; after run, calls the judge |
| `src/interceptor.py` | gate between "model decided" and "tool ran". logs every decision |
| `src/policy.py` | yaml load + pure check logic (no I/O beyond reading the policy file) |
| `src/judge.py` | outcome check: transcript (CALLED + RESULT + SAID) → separate Claude verdict pass/fail |
| `policies/` | task-scoped rules. swap file = swap what the task may do |
| `logs/` | append-only jsonl audit trail |
| `tests/test_interceptor.py` | policy/interceptor proof **without** an agent LLM |
| `tests/test_judge.py` | judge proof with hand-written transcripts (**needs** api key; skips the agent) |

### request flow (one tool call)

1. user runs agent with a task string + path to a policy yaml.
2. `run_agent` loads the policy once, sends messages (+ tools) to the model.
3. if `stop_reason == tool_use`, for each tool block:
   - print `[tool call] ...`
   - `audited_execute(name, input, policy, execute_tool)`
4. interceptor: `check_action` → if allowed, call `execute_tool`; else return a block string to the model.
5. interceptor always appends one json line to the log and prints `[audit] ALLOWED|BLOCKED`.
6. tool results go back into the conversation; loop until the model stops calling tools or `max_turns` hits.
7. CLI then builds a transcript via `summarize_transcript` (must include `RESULT:` lines) and calls `judge_run` → prints `--- judge verdict ---`.

### policy check order

important — order is intentional:

1. **forbidden_tools** — hard deny
2. **allowed_tools** — if the list is non-empty, tool must be on it
3. **allowed_paths** — only when tool input has `path`; must `startswith` a listed prefix

### trust boundary

- **model judgment** = first line (may refuse injection on its own).
- **interceptor** = independent second line; does not care why the model called the tool. checks *allowed actions*, not *good outcomes*.
- **judge** = third line; checks whether the transcript shows the task was actually done (complete + grounded in tool results). a run can pass the interceptor and fail the judge (or the reverse, in theory).
- never put real network/fs/email behind `execute_tool` without keeping the interceptor in the middle.
- never feed the judge a transcript that omits tool `RESULT`s — it will just trust the agent's `SAID` claims (critical bug; fixed).

---

## how to run

always from the **repo root** (policy paths, log paths, and `.env` assume that).

### setup

```bash
pip install -r requirements.txt
```

`.env` (gitignored):

```
ANTHROPIC_API_KEY=sk-ant-...
```

deps: `anthropic`, `pyyaml`, `python-dotenv` (`requirements.txt`).

### agent (needs api key)

```bash
# defaults: summarize /data/report.txt, policies/summarize_report.yaml, claude-sonnet-4-6
python src/agent.py

# custom: task, policy, optional model, optional --naive (follow-doc-instructions system prompt)
python src/agent.py "Summarize the report at /data/report.txt for me." policies/summarize_report.yaml
python src/agent.py "Summarize and save to /data/summary.txt" policies/summarize_and_save.yaml claude-haiku-4-5
python src/agent.py "Summarize the report at /data/report.txt for me." policies/summarize_report.yaml claude-sonnet-4-6 --naive
```

CLI shape: `python src/agent.py [task] [policy_path] [model] [--naive]`

### interceptor tests (no api key)

```bash
python tests/test_interceptor.py
```

covers: forbidden `send_email`, allowed `read_file` under `/data/`, blocked `read_file` on `/etc/passwd`.

### judge tests (needs api key; no agent)

```bash
python tests/test_judge.py
```

covers: good summary → pass; incomplete (no write) → fail; fabricated (no read) → fail.

### what you should see

- agent: `[tool call] ...` then `[audit] ALLOWED|BLOCKED — ...`, then `--- final response ---`, then `--- judge verdict ---`
- interceptor tests: three `PASS:` lines + `All interceptor tests passed.`
- judge tests: `[good|incomplete|fabricated run]` verdict lines + three `PASS:` lines + `All judge tests passed.`
- logs: `logs/actions.jsonl` (agent), `logs/test_actions.jsonl` (interceptor tests)

---

## layout

```
Agent-Auditor/
├── skills.md                 ← you are here (master; self-improving)
├── .cursor/rules/
│   └── update-skills-md.mdc  ← always-on: update root skills.md after findings/critical fixes
├── README.md                 ← human-facing demo writeup
├── requirements.txt
├── .env                      ← ANTHROPIC_API_KEY (local only)
├── src/
│   ├── agent.py
│   ├── interceptor.py
│   ├── policy.py
│   ├── judge.py
│   └── skills.md
├── policies/
│   ├── summarize_report.yaml
│   ├── summarize_and_save.yaml
│   └── skills.md
├── tests/
│   ├── test_interceptor.py
│   ├── test_judge.py
│   └── skills.md
└── logs/
    ├── actions.jsonl
    ├── test_actions.jsonl
    └── skills.md
```

---

## deploy

no deploy target. local demo only — no server, docker, or cloud package.

"ship" = clone → `pip install -r requirements.txt` → set `.env` → run from root.

do not commit `.env`. do not treat `FAKE_FS` / fake `send_email` as production I/O.

---

## debug (quick)

| symptom | check |
|---------|--------|
| `ModuleNotFoundError: policy` | cwd not repo root, or broken `sys.path` in tests |
| auth / missing key | root `.env` has `ANTHROPIC_API_KEY` |
| no `[audit]` lines | model never called a tool (text-only refuse), or wrong stdout |
| `FileNotFoundError` on yaml | policy path wrong; must be relative to root |
| expected block didn't happen | tool name spelling vs yaml; path prefix `startswith`; see `reason` in jsonl |
| judge passes fabricated answers | transcript missing `RESULT:` lines — `summarize_transcript` must include tool returns, not only CALLED/SAID |
| judge returns `verdict: error` | model didn't return parseable JSON; see `reason` raw text |

deeper notes: the per-directory `skills.md` files.

---

## findings log

append-only learning surface. **newest first.** agents: see [self-improve protocol](#self-improve-protocol).

### 2026-09-23 — judge transcript omitted tool results
- **type:** critical-fix
- **what:** first `summarize_transcript` only emitted CALLED/SAID. judge could not tell a grounded summary from a fabricated one because it never saw real tool returns. fixed to emit `RESULT:` lines from `tool_result` blocks (dicts built in `agent.py`).
- **why it matters:** without RESULT lines the judge is just trusting the agent — same class of failure the judge exists to catch.
- **fix or follow-up:** `src/judge.py` includes RESULT; `tests/test_judge.py` covers good / incomplete / fabricated. interceptor ≠ judge: policy vs outcome. both are required.

### 2026-09-23 — master skills is the project memory
- **type:** finding
- **what:** root `skills.md` is the living runbook + architecture map; per-dir `skills.md` files are detail. agents must update the root file on findings and critical fixes so later sessions inherit the knowledge.
- **why it matters:** without this, every chat re-learns cwd/policy/interceptor quirks and overclaims demo results.
- **fix or follow-up:** self-improve protocol + this log; Cursor rule `.cursor/rules/update-skills-md.mdc` (`alwaysApply: true`).

### 2026-09-25 — break-it trial count was 6, not 5
- **type:** finding
- **what:** README "trying to actually break it" undercounted trials as "5 combos." corrected to 6 trials varying model (sonnet/haiku), system prompt (none/naive), and injection wording (casual note vs fake system override). worst-case: haiku + naive + aggressive injection — still no `send_email`.
- **why it matters:** wrong count makes the experiment look sloppier than it was; keep the writeup accurate.
- **fix or follow-up:** README paragraph replaced; takeaway paragraph left unchanged.

### 2026-09-16 — models refuse injection; interceptor still required
- **type:** finding
- **what:** across agent runs (including 6 break-it trials varying sonnet/haiku, none/naive system prompt, casual vs `[SYSTEM OVERRIDE]` injection), the model refused `send_email` every time — interceptor never saw a live violation. direct tests in `tests/test_interceptor.py` still prove block/allow/path checks work without an LLM.
- **why it matters:** "demo caught injection" ≠ "policy layer was stress-tested by the model." don't trust model self-defense as the only control; keep the independent check.
- **fix or follow-up:** no product bug. document honestly in README; use interceptor tests to prove the gate. still unknown: which weaker model or subtler injection finally gets through.
