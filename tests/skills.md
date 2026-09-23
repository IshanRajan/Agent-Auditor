# skills — tests/

how to run, extend, and debug the direct tests (interceptor + judge).

## what this dir is

- `test_interceptor.py` — policy + interceptor, no llm, no api key
- `test_judge.py` — hand-written transcripts into `judge_run`, skips the agent, **needs** api key

interceptor tests prove allow/deny without waiting for the model to misbehave.
judge tests prove pass/fail on good, incomplete, and fabricated transcripts.

## run

from repo root (required — policy paths and log paths are root-relative):

```bash
python tests/test_interceptor.py
python tests/test_judge.py
```

interceptor expected: three `PASS:` lines, then `All interceptor tests passed.`, plus `[audit]` lines. writes `logs/test_actions.jsonl` (append).

judge expected: `[good|incomplete|fabricated run]` verdict lines, three `PASS:` lines, then `All judge tests passed.`

plain scripts with asserts (not pytest-first). documented path is running the files directly.

## deploy

nothing to deploy. same commands in ci/local:

```bash
pip install -r requirements.txt
python tests/test_interceptor.py
python tests/test_judge.py   # needs ANTHROPIC_API_KEY
```

## debug

### test_interceptor.py

- `FileNotFoundError` on `policies/summarize_report.yaml` → not running from repo root.
- `ModuleNotFoundError: policy` → `sys.path` insert failed; don't break the path bootstrap at the top of the file.
- assert fails on forbidden case → check `forbidden_tools` / `check_action` order in `policy.py`.
- assert fails on allowed case → result should start with `(real tool would have run)`; `BLOCKED by policy` means allow-list/path too tight or tool name mismatch.
- out-of-scope path not blocked → `allowed_paths` missing or no `"path"` in tool_input.
- noisy `logs/test_actions.jsonl` → safe to truncate; tests append every run.

### test_judge.py

- auth errors → root `.env` missing `ANTHROPIC_API_KEY`.
- fabricated case unexpectedly passes → judge prompt too soft, or you're not including the lack of CALLED/RESULT in the fake transcript.
- incomplete case unexpectedly passes → task string must clearly require the write step.
- flaky wording in printed reason is ok; asserts are on `verdict` only (`pass`/`fail`).

adding an interceptor case: copy a `test_*`, call `audited_execute` with `fake_execute`, assert, print `PASS:`, wire into `__main__`.

adding a judge case: hand-write a compact transcript with CALLED/RESULT/SAID as needed, call `judge_run`, assert `verdict`, print `PASS:`, wire into `__main__`.
