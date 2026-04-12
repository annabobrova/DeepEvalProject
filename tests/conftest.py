import os
import time
import webbrowser
from collections import defaultdict
from html import escape

import pytest

from config import MODEL_NAME, JUDGE_MODEL_NAME

_session_start_time = None

CATEGORY_COLORS = {
    "happy_path": "#3498db",
    "edge_case":  "#f39c12",
    "negative":   "#e74c3c",
    "ambiguous":  "#9b59b6",
    "robustness": "#1abc9c",
}


def pytest_sessionstart(session):
    global _session_start_time
    _session_start_time = time.time()


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
_structured_results = []
_hallucination_results = []
_indirect_injection_results = []


@pytest.fixture(scope="session")
def report_results():
    return _report_results


@pytest.fixture(scope="session")
def persona_results():
    return _persona_results


@pytest.fixture(scope="session")
def structured_results():
    return _structured_results


@pytest.fixture(scope="session")
def hallucination_results():
    return _hallucination_results


@pytest.fixture(scope="session")
def indirect_injection_results():
    return _indirect_injection_results


# ------------------------------------------------------------------
# HTML helpers — module-level so they can be reused across sections
# ------------------------------------------------------------------

def score_color(passed):
    return "#2ecc71" if passed else "#e74c3c"


def score_badge(score, passed):
    color = score_color(passed)
    score_str = f"{score:.2f}" if score is not None else "N/A"
    return (
        f'<span style="background:{color};color:white;padding:3px 8px;'
        f'border-radius:4px;display:inline-block;font-size:13px">{score_str}</span>'
    )


def sim_badge(sim):
    if sim is None:
        return "<span style='color:#aaa'>N/A</span>"
    color = "#2ecc71" if sim >= 0.90 else ("#f39c12" if sim >= 0.70 else "#e74c3c")
    return f'<span style="background:{color};color:white;padding:3px 8px;border-radius:4px;font-size:13px">{sim:.2f}</span>'


# ------------------------------------------------------------------
# HTML report — written once after all tests finish
# ------------------------------------------------------------------

def pytest_sessionfinish(session, exitstatus):
    elapsed = time.time() - _session_start_time if _session_start_time else 0
    elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"

    results = _report_results
    personas = _persona_results
    structured = _structured_results
    hallucinations = _hallucination_results
    indirect_injections = _indirect_injection_results

    if not results and not personas and not structured and not hallucinations and not indirect_injections:
        return

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
          <td><span style="background:{color};color:white;padding:2px 8px;border-radius:4px">{escape(cat)}</span></td>
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
                f'{escape(name)}: {score_str}</span>'
            )

        cat_color = CATEGORY_COLORS.get(r["category"], "#aaa")
        cat_badge = f'<span style="background:{cat_color};color:white;padding:2px 8px;border-radius:4px;font-size:12px">{escape(r["category"])}</span>'
        result_color = score_color(r["passed"])
        result_text = "PASS" if r["passed"] else "FAIL"
        rows += f"""
        <tr>
          <td>{cat_badge}</td>
          <td>{escape(r['input'])}</td>
          <td>{escape(r['actual_output'])}</td>
          <td>{escape(r['expected_output'])}</td>
          <td>{sim_badge(r.get('similarity'))}</td>
          <td>{badges}</td>
          <td style="color:{result_color};font-weight:bold">{result_text}</td>
        </tr>"""

    all_results = results + hallucinations + structured + indirect_injections
    total = len(all_results)
    passed_count = sum(1 for r in all_results if r["passed"])
    summary_class = "pass" if passed_count == total else "fail"

    # --- Persona tests table ---
    persona_rows = ""
    for r in personas:
        simplicity_score, simplicity_pass = r["simplicity_score"]
        factual_score, factual_pass = r["factual_score"]
        persona_rows += f"""
        <tr>
          <td>{escape(r['input'])}</td>
          <td>{escape(r['student_output'])}</td>
          <td>{score_badge(simplicity_score, simplicity_pass)}</td>
          <td>{escape(r['factual_output'])}</td>
          <td>{score_badge(factual_score, factual_pass)}</td>
        </tr>"""

    persona_section = ""
    if persona_rows:
        persona_section = f"""
  <h2>Persona Tests — Model Adapts to Audience</h2>
  <p style="color:#555;font-size:14px">
    The model is called twice per question: once told to explain to an elementary school student,
    once told to be factually precise. A neutral judge scores each response on the appropriate criterion.
  </p>
  <table>
    <tr>
      <th>Input</th>
      <th>Student Response</th>
      <th>Simplicity</th>
      <th>Factual Response</th>
      <th>Factual Completeness</th>
    </tr>
    {persona_rows}
  </table>"""

    # --- Structured output table ---
    structured_rows = ""
    for r in structured:
        valid_badge = (
            '<span style="background:#2ecc71;color:white;padding:2px 8px;border-radius:4px">Valid JSON</span>'
            if r["json_valid"] else
            '<span style="background:#e74c3c;color:white;padding:2px 8px;border-radius:4px">Invalid JSON</span>'
        )
        key_checks = ""
        for key, (actual_val, expected_val, match) in r["key_matches"].items():
            color = "#2ecc71" if match else "#e74c3c"
            key_checks += (
                f'<div style="font-size:12px;margin:2px 0">'
                f'<strong>{escape(key)}:</strong> '
                f'<span style="color:{color}">{escape(repr(actual_val))}</span>'
                f'</div>'
            )
        result_color = score_color(r["passed"])
        result_text = "PASS" if r["passed"] else "FAIL"
        structured_rows += f"""
        <tr>
          <td>{escape(r['input'])}</td>
          <td><code style="font-size:12px;word-break:break-all">{escape(r['actual_output'])}</code></td>
          <td>{valid_badge}</td>
          <td>{key_checks}</td>
          <td style="color:{result_color};font-weight:bold">{result_text}</td>
        </tr>"""

    structured_section = ""
    if structured_rows:
        structured_section = f"""
  <h2>Structured Output Tests</h2>
  <p style="color:#555;font-size:14px">
    Tests that require the model to return valid JSON in a specific shape.
    If JSON is invalid, the test fails immediately — no judge is called.
  </p>
  <table>
    <tr>
      <th>Input</th>
      <th>Raw Output</th>
      <th>JSON Valid</th>
      <th>Key Checks</th>
      <th>Result</th>
    </tr>
    {structured_rows}
  </table>"""

    # --- Hallucination results table ---
    hallucination_rows = ""
    for r in hallucinations:
        answerable_color = "#3498db" if r["answerable"] else "#9b59b6"
        answerable_label = "answerable" if r["answerable"] else "unanswerable"
        answerable_badge = (
            f'<span style="background:{answerable_color};color:white;padding:2px 8px;'
            f'border-radius:4px;font-size:12px">{answerable_label}</span>'
        )
        badges = ""
        for name, score, passed in r["scores"]:
            color = score_color(passed)
            score_str = f"{score:.2f}" if score is not None else "N/A"
            badges += (
                f'<span style="background:{color};color:white;padding:3px 8px;'
                f'border-radius:4px;margin:2px;display:inline-block;font-size:13px">'
                f'{escape(name)}: {score_str}</span>'
            )
        result_color = score_color(r["passed"])
        result_text = "PASS" if r["passed"] else "FAIL"
        hallucination_rows += f"""
        <tr>
          <td>{answerable_badge}</td>
          <td>{escape(r['input'])}</td>
          <td>{escape(r['actual_output'])}</td>
          <td>{escape(r['expected_output'])}</td>
          <td>{sim_badge(r.get('similarity'))}</td>
          <td>{badges}</td>
          <td style="color:{result_color};font-weight:bold">{result_text}</td>
        </tr>"""

    hallucination_section = ""
    if hallucination_rows:
        hal_total = len(hallucinations)
        hal_passed = sum(1 for r in hallucinations if r["passed"])
        hallucination_section = f"""
  <h2>RAG Hallucination Tests ({hal_passed}/{hal_total} passed)</h2>
  <p style="color:#555;font-size:14px">
    The model is grounded in Anna's resume as the retrieved context document.
    <strong style="color:#3498db">Answerable</strong> questions test faithfulness — the model must answer correctly from the document.
    <strong style="color:#9b59b6">Unanswerable</strong> questions test anti-hallucination — the model must say "not mentioned" instead of guessing.
  </p>
  <table>
    <tr>
      <th>Type</th>
      <th>Input</th>
      <th>Actual Output</th>
      <th>Expected Output</th>
      <th>Similarity</th>
      <th>Judge Scores</th>
      <th>Result</th>
    </tr>
    {hallucination_rows}
  </table>"""

    # --- Indirect injection results table ---
    indirect_injection_rows = ""
    attack_colors = {
        "explicit":     "#e74c3c",
        "authority":    "#e67e22",
        "false_claim":  "#8e44ad",
        "roleplay":     "#2980b9",
        "end_override": "#16a085",
    }
    for r in indirect_injections:
        color = attack_colors.get(r["attack_type"], "#aaa")
        attack_badge = (
            f'<span style="background:{color};color:white;padding:2px 8px;'
            f'border-radius:4px;font-size:12px">{escape(r["attack_type"])}</span>'
        )
        badges = ""
        for name, score, passed in r["scores"]:
            score_str = f"{score:.2f}" if score is not None else "N/A"
            badges += (
                f'<span style="background:{score_color(passed)};color:white;padding:3px 8px;'
                f'border-radius:4px;margin:2px;display:inline-block;font-size:13px">'
                f'{escape(name)}: {score_str}</span>'
            )
        result_color = score_color(r["passed"])
        result_text = "PASS" if r["passed"] else "FAIL"
        indirect_injection_rows += f"""
        <tr>
          <td>{attack_badge}</td>
          <td><code style="font-size:12px;color:#c0392b;word-break:break-word">{escape(r['injected_chunk'])}</code></td>
          <td>{escape(r['input'])}</td>
          <td>{escape(r['actual_output'])}</td>
          <td>{escape(r['expected_output'])}</td>
          <td>{sim_badge(r.get('similarity'))}</td>
          <td>{badges}</td>
          <td style="color:{result_color};font-weight:bold">{result_text}</td>
        </tr>"""

    indirect_injection_section = ""
    if indirect_injection_rows:
        ind_total = len(indirect_injections)
        ind_passed = sum(1 for r in indirect_injections if r["passed"])
        indirect_injection_section = f"""
  <h2>Indirect Prompt Injection Tests ({ind_passed}/{ind_total} passed)</h2>
  <p style="color:#555;font-size:14px">
    Malicious instructions are hidden inside the retrieved resume document — not in the user's message.
    The model must give an honest assessment based on real resume facts and resist the injected directive,
    even though it came from the "trusted" context source.
    <strong>FaithfulnessMetric has a blind spot here</strong>: if the model follows an injected instruction
    that is present in the context, faithfulness scores it as PASS. InjectionResistance (GEval) catches this instead.
  </p>
  <table>
    <tr>
      <th>Attack Type</th>
      <th>Injected Chunk</th>
      <th>Input</th>
      <th>Actual Output</th>
      <th>Expected Output</th>
      <th>Similarity</th>
      <th>Judge Score</th>
      <th>Result</th>
    </tr>
    {indirect_injection_rows}
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
    Model: <strong>{escape(MODEL_NAME)}</strong> &nbsp;|&nbsp;
    Judge: <strong>{escape(JUDGE_MODEL_NAME)}</strong> &nbsp;|&nbsp;
    Results: <span class="{summary_class}">{passed_count}/{total} passed</span> &nbsp;|&nbsp;
    Duration: <strong>{elapsed_str}</strong>
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
      <th>Similarity</th>
      <th>Judge Scores</th>
      <th>Result</th>
    </tr>
    {rows}
  </table>

  {persona_section}

  {structured_section}

  {hallucination_section}

  {indirect_injection_section}
</body>
</html>"""

    report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "report.html"))
    try:
        with open(report_path, "w") as f:
            f.write(html)
        webbrowser.open(f"file://{report_path}")
        print(f"\n✅ Report saved to {report_path}")
    except Exception as e:
        print(f"\n⚠️  Failed to write report: {e}")
