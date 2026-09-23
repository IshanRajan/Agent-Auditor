# skills — tests/

how to run, extend, and debug the interceptor tests.

## what this dir is

- `test_interceptor.py` — direct tests of policy + interceptor, no llm, no api key

proves the audit layer blocks/allows correctly even when the model never tries a bad tool call.

## run

from repo root (required — policy paths and log paths are root-relative):

```bash
python tests/test_interceptor.py
```

expected: three `PASS:` lines, then `All interceptor tests passed.`, plus `[audit]` lines on stdout.

writes to `logs/test_actions.jsonl` (append).

does not use pytest by default; it's a plain script with asserts. you can still collect it with pytest if you want, but the documented path is running the file directly.

## deploy

nothing to deploy. run in ci or locally the same way:

```bash
pip install -r requirements.txt
python tests/test_interceptor.py
```

no anthropic key required for these tests.

## debug

- `FileNotFoundError` on `policies/summarize_report.yaml` → not running from repo root.
- `ModuleNotFoundError: policy` → `sys.path` insert failed; run the file as above, don't break the path bootstrap at the top of the test file.
- assert fails on forbidden case → interceptor/policy allow logic regressed; check `forbidden_tools` in the yaml and `check_action` order in `policy.py`.
- assert fails on allowed case → result should start with `(real tool would have run)`; if you see `BLOCKED by policy`, allow-list/path rules are too tight or tool name mismatch.
- out-of-scope path not blocked → `allowed_paths` missing or path check skipped (only runs when `"path"` is in tool_input).
- noisy / huge `logs/test_actions.jsonl` → safe to delete or truncate; tests append every run.

adding a case: copy a `test_*` function, call `audited_execute` with `fake_execute`, assert on the returned string, print a `PASS:` line, and invoke it from `if __name__ == "__main__"`.
