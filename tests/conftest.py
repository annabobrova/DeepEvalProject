import os
import webbrowser
from collections import defaultdict

import pytest

from config import MODEL_NAME, JUDGE_MODEL_NAME

CATEGORY_COLORS = {
    "happy_path": "#3498db",
    "edge_case":  "#f39c12",
    "negative":   "#e74c3c",
    "ambiguous":  "#9b59b6",
    "robustness": "#1abc9c",
}

# ------------------------------------------------------------------
# Category markers
# ------------------------------------------------------------------

def pytest_collection_modifyitems(items):
    for item in items:
        if hasattr(item, "callspec") and "example" in item.callspec.params:
            category = item.callspec.params["example"].get("category")
            if category:
                item.add_marker(getattr(pytest.mark, category))


# ------------------------------------------------------------------
# Session-scoped stores
# ------------------------------------------------------------------

_report_results = []
_persona_results = []


@pytest.fixture(scope="session")
def report_results():
    return _report_results


@pytest.fixture(scope="session")
def persona_results():
    return _persona_results


# ------------------------------------------------------------------
# HTML report — written once after all tests finish
# ------------------------------------------------------------------

def pytest_sessionfinish(session, exitstatus):
    results = _report_results
    personas = _persona_results

    if not results and not personas:
        return

    def score_color(passed):
        return "#2ecc71" if passed else "#e74c3c"

    # --- Main results table ---
    by_category = defaultdict(list)
    for r in results:
        by_category[r["category"]].append(r)

    summary_rows = ""
    for cat, items in by_category.items():
        passed_in_cat = sum(1 for r in items if r["passed"])
        color = CATEGORY_COLORS.get(cat, "#aaa")
        summary_rows += f"""
        <tr>
          <td><span style="background:{color};color:white;padding:2px 8px;border-radius:4px">{cat}</span></td>
          <td>{passed_in_cat}/{len(items)}</td>
        </tr>"""

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

        cat_color = CATEGORY_COLORS.get(r["category"], "#aaa")
        cat_badge = f'<span style="background:{cat_color};color:white;padding:2px 8px;border-radius:4px;font-size:12px">{r["category"]}</span>'
        result_color = score_color(r["passed"])
        result_text = "PASS" if r["passed"] else "FAIL"
        rows += f"""
        <tr>
          <td>{cat_badge}</td>
          <td>{r['input']}</td>
          <td>{r['actual_output']}</td>
          <td>{r['expected_output']}</td>
          <td>{badges}</td>
          <td style="color:{result_color};font-weight:bold">{result_text}</td>
        </tr>"""

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    summary_class = "pass" if passed_count == total else "fail"

    # --- Judge persona comparison table ---
    persona_rows = ""
    for r in personas:
        linguist_score, linguist_pass = r["scores"].get("ElementaryStudentJudge", (None, False))
        factchecker_score, factchecker_pass = r["scores"].get("FactCheckerJudge", (None, False))

        def badge(score, passed):
            color = score_color(passed)
            score_str = f"{score:.2f}" if score is not None else "N/A"
            return (
                f'<span style="background:{color};color:white;padding:3px 8px;'
                f'border-radius:4px;display:inline-block;font-size:13px">{score_str}</span>'
            )

        persona_rows += f"""
        <tr>
          <td>{r['input']}</td>
          <td>{r['actual_output']}</td>
          <td>{badge(linguist_score, linguist_pass)}</td>
          <td>{badge(factchecker_score, factchecker_pass)}</td>
        </tr>"""

    persona_section = ""
    if persona_rows:
        persona_section = f"""
  <h2>Judge Persona Comparison (happy_path)</h2>
  <p style="color:#555;font-size:14px">
    <strong>ElementaryStudentJudge</strong> scores on simplicity — would an elementary school student understand this? &nbsp;|&nbsp;
    <strong>FactCheckerJudge</strong> scores only on whether the core fact is present.
  </p>
  <table>
    <tr>
      <th>Input</th>
      <th>Actual Output</th>
      <th>ElementaryStudentJudge</th>
      <th>FactCheckerJudge</th>
    </tr>
    {persona_rows}
  </table>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>DeepEval Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; background: #f9f9f9; }}
    h1, h2 {{ color: #333; }}
    .summary {{ margin-bottom: 20px; font-size: 16px; }}
    .pass {{ color: #2ecc71; font-weight: bold; }}
    .fail {{ color: #e74c3c; font-weight: bold; }}
    table {{ width: 100%; border-collapse: collapse; background: white; box-shadow: 0 1px 4px rgba(0,0,0,0.1); margin-bottom: 40px; }}
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

  <h2>Summary by Category</h2>
  <table style="width:300px">
    <tr><th>Category</th><th>Pass Rate</th></tr>
    {summary_rows}
  </table>

  <h2>All Results</h2>
  <table>
    <tr>
      <th>Category</th>
      <th>Input</th>
      <th>Actual Output</th>
      <th>Expected Output</th>
      <th>Scores</th>
      <th>Result</th>
    </tr>
    {rows}
  </table>

  {persona_section}
</body>
</html>"""

    report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "report.html"))
    with open(report_path, "w") as f:
        f.write(html)

    webbrowser.open(f"file://{report_path}")
    print(f"\n✅ Report saved to {report_path}")
