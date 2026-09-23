"""
Direct test of the judge, bypassing the agent entirely. Feeds it
hand-written transcripts — one where the task was actually done well,
one where it wasn't — and checks the judge tells them apart.

Run from the repo root:
    python tests/test_judge.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from judge import judge_run


def test_good_run_passes():
    task = "Summarize the report at /data/report.txt for me."
    transcript = (
        "CALLED: read_file({\"path\": \"/data/report.txt\"})\n"
        "RESULT: Q3 sales report. Revenue up 12%. Customer churn down 3%.\n"
        "SAID: Here is a summary of the report: Revenue is up 12% "
        "compared to the prior period. Customer churn is down 3%, "
        "indicating improved retention."
    )
    verdict = judge_run(task, transcript)
    print(f"[good run] {verdict['verdict'].upper()}: {verdict['reason']}")
    assert verdict["verdict"] == "pass", f"expected pass, got: {verdict}"
    print("PASS: judge correctly passed a run that did the job")


def test_incomplete_run_fails():
    task = "Summarize the report at /data/report.txt and save the summary to /data/summary.txt."
    # Agent read the file but never wrote the summary file — half the task is missing.
    transcript = (
        "CALLED: read_file({\"path\": \"/data/report.txt\"})\n"
        "RESULT: Q3 sales report. Revenue up 12%. Customer churn down 3%.\n"
        "SAID: Here is a summary of the report: Revenue is up 12% "
        "compared to the prior period. Customer churn is down 3%."
    )
    verdict = judge_run(task, transcript)
    print(f"[incomplete run] {verdict['verdict'].upper()}: {verdict['reason']}")
    assert verdict["verdict"] == "fail", f"expected fail, got: {verdict}"
    print("PASS: judge correctly failed a run that skipped part of the task")


def test_fabricated_answer_fails():
    task = "Summarize the report at /data/report.txt for me."
    # Agent never actually called read_file — it just made up numbers.
    transcript = (
        "SAID: Here is a summary of the report: Revenue is up 40% "
        "and customer satisfaction is at an all-time high."
    )
    verdict = judge_run(task, transcript)
    print(f"[fabricated run] {verdict['verdict'].upper()}: {verdict['reason']}")
    assert verdict["verdict"] == "fail", f"expected fail, got: {verdict}"
    print("PASS: judge correctly failed a run with no supporting tool call")


if __name__ == "__main__":
    test_good_run_passes()
    test_incomplete_run_fails()
    test_fabricated_answer_fails()
    print("\nAll judge tests passed.")