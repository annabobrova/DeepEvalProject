import subprocess
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, GEval

from datasets.golden_set import GOLDEN_SET
from model import generate
from judge import ClaudeJudge
from config import MODEL_NAME, JUDGE_MODEL_NAME


# ------------------------------------------------------------------
# Session-scoped store for the HTML report
# ------------------------------------------------------------------

@pytest.fixture(scope="session")
def report_results():
    return []


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

@pytest.mark.parametrize("example", GOLDEN_SET)
def test_model_on_golden_set(example, report_results):
    # Fresh metrics per test — avoids stale state between runs
    judge = ClaudeJudge()
    answer_relevancy = AnswerRelevancyMetric(threshold=0.7, model=judge)
    faithfulness = FaithfulnessMetric(threshold=0.7, model=judge)
    correctness = GEval(
        name="Correctness",
        criteria="Determine whether the actual output is factually correct compared to the expected output.",
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        threshold=0.7,
        verbose_mode=True,
        model=judge,
    )

    actual_output = generate(example["input"])

    test_case = LLMTestCase(
        input=example["input"],
        actual_output=actual_output,
        expected_output=example["expected_output"],
        retrieval_context=example["context"] if example["context"] else None,
    )

    metrics = [answer_relevancy, correctness]
    if example["context"]:
        metrics.append(faithfulness)

    print(f"\n--- Scores for: {example['input'][:50]} ---")
    for m in metrics:
        m.measure(test_case)
        print(f"  {m.__class__.__name__}: {m.score:.2f} ({'PASS' if m.is_successful() else 'FAIL'})")

    report_results.append({
        "input": example["input"],
        "actual_output": actual_output,
        "expected_output": example["expected_output"],
        "scores": [(m.__class__.__name__, m.score, m.is_successful()) for m in metrics],
        "passed": all(m.is_successful() for m in metrics),
    })

    assert_test(test_case, metrics)


# ------------------------------------------------------------------
# HTML report — written once after all tests finish
# ------------------------------------------------------------------

def pytest_sessionfinish(session, exitstatus):
    # Retrieve results from the fixture store
    results = []
    for item in session.items:
        if hasattr(item, "_report_results"):
            results = item._report_results
            break

    # Fall back: collect from fixture cache
    try:
        fm = session._fixturemanager
        for key, val in fm._arg2fixturedefs.items():
            if key == "report_results":
                fixture_def = val[0]
                if hasattr(fixture_def, "cached_result") and fixture_def.cached_result:
                    results = fixture_def.cached_result[0]
                    break
    except Exception:
        pass

    if not results:
        return

    def score_color(passed):
        return "#2ecc71" if passed else "#e74c3c"

    rows = ""
    for r in results:
        badges = ""
        for name, score, passed in r["scores"]:
            color = score_color(passed)
            score_str = f"{score:.2f}" if score is not None else "N/A"
            badges += (
                f'<span style="background:{color};color:white;padding:3px 8px;'
                f'border-radius:4px;margin:2px;display:inline-block;font-size:13px">'
                f'{name}: {score_str}</span>'
            )

        result_color = score_color(r["passed"])
        result_text = "PASS" if r["passed"] else "FAIL"
        rows += f"""
        <tr>
          <td>{r['input']}</td>
          <td>{r['actual_output']}</td>
          <td>{r['expected_output']}</td>
          <td>{badges}</td>
          <td style="color:{result_color};font-weight:bold">{result_text}</td>
        </tr>"""

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    summary_class = "pass" if passed_count == total else "fail"

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>DeepEval Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; background: #f9f9f9; }}
    h1 {{ color: #333; }}
    .summary {{ margin-bottom: 20px; font-size: 16px; }}
    .pass {{ color: #2ecc71; font-weight: bold; }}
    .fail {{ color: #e74c3c; font-weight: bold; }}
    table {{ width: 100%; border-collapse: collapse; background: white; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }}
    th {{ background: #333; color: white; padding: 12px; text-align: left; }}
    td {{ padding: 12px; border-bottom: 1px solid #eee; vertical-align: top; }}
    tr:hover {{ background: #f5f5f5; }}
  </style>
</head>
<body>
  <h1>DeepEval Report</h1>
  <div class="summary">
    Model: <strong>{MODEL_NAME}</strong> &nbsp;|&nbsp;
    Judge: <strong>{JUDGE_MODEL_NAME}</strong> &nbsp;|&nbsp;
    Results: <span class="{summary_class}">{passed_count}/{total} passed</span>
  </div>
  <table>
    <tr>
      <th>Input</th>
      <th>Actual Output</th>
      <th>Expected Output</th>
      <th>Scores</th>
      <th>Result</th>
    </tr>
    {rows}
  </table>
</body>
</html>"""

    report_path = "report.html"
    with open(report_path, "w") as f:
        f.write(html)

    subprocess.run(["open", report_path])
    print(f"\n✅ Report saved to {report_path}")
