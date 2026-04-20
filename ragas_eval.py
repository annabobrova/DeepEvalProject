"""
ragas_eval.py — Evaluate the RAG pipeline using the RAGAs library.

RAGAs is a framework purpose-built for RAG evaluation. Unlike DeepEval (which
uses pytest and lets you write custom GEval criteria), RAGAs runs fixed metric
formulas and is invoked as a plain Python script.

Three metrics are run against HALLUCINATION_SET (10 resume questions):

  Faithfulness    — are the model's claims supported by the retrieved context?
                    High score = model only says what the resume says.
                    Low score  = model invented facts not in the resume.
                    Inputs: user_input, response, retrieved_contexts

  AnswerRelevancy — does the answer actually address the question?
                    Scored with embeddings (not LLM) — measures semantic overlap
                    between question and answer.
                    Inputs: user_input, response

  ContextRecall   — does the retrieved context contain enough to answer?
                    The LLM decomposes the reference answer into atomic claims,
                    then checks which claims are present in the context.
                    High score = context is sufficient. Low = important info missing.
                    Inputs: user_input, retrieved_contexts, reference

Usage:
    python3.11 ragas_eval.py

To add more metrics: import from ragas.metrics.collections, instantiate with llm=,
and add a scoring call in run_evaluation(). Example: ContextPrecision, ContextEntityRecall.

To use a different dataset: replace HALLUCINATION_SET with any list of dicts
that has keys: input, expected_output, context.
"""

import os
import time
import webbrowser
from html import escape

from tabulate import tabulate
from ragas.metrics.collections import AnswerRelevancy, ContextRecall, Faithfulness

from model import generate
from rag.hallucination_set import HALLUCINATION_SET
from ragas_config import make_ragas_embeddings, make_ragas_llm


# ── RAG system prompt (same as test_golden_set.py) ───────────────────────────

def _rag_system_prompt(context):
    return (
        "You are a helpful assistant answering questions based only on the provided document. "
        "If the document does not contain the answer, say so clearly — do not guess or invent information.\n\n"
        "Document:\n" + "\n".join(context)
    )


# ── Step 1: collect model outputs ────────────────────────────────────────────

def build_rows(dataset):
    """
    Call the model for each question and collect inputs for RAGAs metrics.

    Returns a list of dicts with all fields each metric may need:
      user_input         — the question
      response           — what the model actually said
      retrieved_contexts — the resume chunks (list of strings)
      reference          — the expected/ideal answer (needed by ContextRecall)
      answerable         — whether the resume can answer this question
    """
    rows = []
    total = len(dataset)
    for i, example in enumerate(dataset, 1):
        print(f"  [{i}/{total}] {example['input'][:70]}")
        actual_output = generate(
            example["input"],
            system=_rag_system_prompt(example["context"]),
        )
        rows.append({
            "user_input": example["input"],
            "response": actual_output,
            "retrieved_contexts": example["context"],
            "reference": example["expected_output"],
            "answerable": example["answerable"],
        })
        if i < total:
            time.sleep(1)   # avoid rate limits — RAGAs also calls the LLM per metric
    return rows


# ── Step 2: run RAGAs metrics ────────────────────────────────────────────────

def run_evaluation():
    print("\n=== RAGAs Evaluation ===")
    print(f"Dataset: HALLUCINATION_SET ({len(HALLUCINATION_SET)} examples)\n")

    # Early connection test — verify auth and URL before generating outputs
    print("Connecting to LLM...", end=" ", flush=True)
    try:
        ragas_llm = make_ragas_llm()
        print("OK")
    except Exception as e:
        print(f"FAILED\n\nCould not initialise LLM: {e}")
        return

    ragas_embeddings = make_ragas_embeddings()

    # Instantiate metrics — each calls the LLM internally when .score() is called
    # To add more: import from ragas.metrics.collections, instantiate with llm=,
    # and add a batch_score call below.
    faithfulness_metric = Faithfulness(llm=ragas_llm)
    answer_relevancy_metric = AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings)
    context_recall_metric = ContextRecall(llm=ragas_llm)

    print("\nStep 1/3 — Generating model responses...")
    rows = build_rows(HALLUCINATION_SET)

    # RAGAs 0.4.x collections metrics use batch_score() directly.
    # Each metric takes only the fields it needs — different per metric.
    print("\nStep 2/3 — Running RAGAs metrics (LLM judge called internally)...")

    faithfulness_scores = faithfulness_metric.batch_score([
        {"user_input": r["user_input"], "response": r["response"], "retrieved_contexts": r["retrieved_contexts"]}
        for r in rows
    ])

    answer_relevancy_scores = answer_relevancy_metric.batch_score([
        {"user_input": r["user_input"], "response": r["response"]}
        for r in rows
    ])

    context_recall_scores = context_recall_metric.batch_score([
        {"user_input": r["user_input"], "retrieved_contexts": r["retrieved_contexts"], "reference": r["reference"]}
        for r in rows
    ])

    print("\nStep 3/3 — Results\n")
    _print_results(rows, faithfulness_scores, answer_relevancy_scores, context_recall_scores)
    _write_html_report(rows, faithfulness_scores, answer_relevancy_scores, context_recall_scores)


# ── Step 3: display results ───────────────────────────────────────────────────

def _print_results(rows, faithfulness_scores, answer_relevancy_scores, context_recall_scores):
    table_rows = []
    for i, (row, f, a, c) in enumerate(
        zip(rows, faithfulness_scores, answer_relevancy_scores, context_recall_scores), 1
    ):
        answerable = "answerable" if row["answerable"] else "unanswerable"
        question = row["user_input"][:50] + "..." if len(row["user_input"]) > 50 else row["user_input"]
        table_rows.append([
            i,
            answerable,
            question,
            f"{f.value:.2f}",
            f"{a.value:.2f}",
            f"{c.value:.2f}",
        ])

    headers = ["#", "Type", "Question", "Faithfulness", "AnswerRelevancy", "ContextRecall"]
    print(tabulate(table_rows, headers=headers, tablefmt="grid"))

    # Averages
    def _avg(scores):
        valid = [s.value for s in scores if s.value == s.value]  # filter nan
        return sum(valid) / len(valid) if valid else float("nan")

    print("\n--- Dataset Averages ---")
    print(f"  Faithfulness:    {_avg(faithfulness_scores):.4f}")
    print(f"  AnswerRelevancy: {_avg(answer_relevancy_scores):.4f}")
    print(f"  ContextRecall:   {_avg(context_recall_scores):.4f}")

    print("\nScore guide:")
    print("  Faithfulness    >0.8 = model stays grounded in context")
    print("  AnswerRelevancy >0.7 = answer addresses the question")
    print("  ContextRecall   >0.7 = context contains enough to answer")


# ── Step 4: HTML report ───────────────────────────────────────────────────────

def _score_badge(value):
    if value != value:  # nan check
        return '<span style="background:#aaa;color:white;padding:3px 8px;border-radius:4px">N/A</span>'
    color = "#2ecc71" if value >= 0.8 else ("#f39c12" if value >= 0.6 else "#e74c3c")
    return f'<span style="background:{color};color:white;padding:3px 8px;border-radius:4px;font-size:13px">{value:.2f}</span>'


def _write_html_report(rows, faithfulness_scores, answer_relevancy_scores, context_recall_scores):
    def _avg(scores):
        valid = [s.value for s in scores if s.value == s.value]
        return sum(valid) / len(valid) if valid else float("nan")

    avg_f = _avg(faithfulness_scores)
    avg_a = _avg(answer_relevancy_scores)
    avg_c = _avg(context_recall_scores)

    table_rows = ""
    for row, f, a, c in zip(rows, faithfulness_scores, answer_relevancy_scores, context_recall_scores):
        type_color = "#3498db" if row["answerable"] else "#9b59b6"
        type_label = "answerable" if row["answerable"] else "unanswerable"
        type_badge = f'<span style="background:{type_color};color:white;padding:2px 8px;border-radius:4px;font-size:12px">{type_label}</span>'
        table_rows += f"""
        <tr>
          <td>{type_badge}</td>
          <td>{escape(row["user_input"])}</td>
          <td style="font-size:13px;color:#555">{escape(row["response"])}</td>
          <td style="font-size:13px;color:#555">{escape(row["reference"])}</td>
          <td>{_score_badge(f.value)}</td>
          <td>{_score_badge(a.value)}</td>
          <td>{_score_badge(c.value)}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>RAGAs Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; background: #f9f9f9; }}
    h1, h2 {{ color: #333; }}
    .summary {{ margin-bottom: 24px; font-size: 15px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; box-shadow: 0 1px 4px rgba(0,0,0,0.1); margin-bottom: 40px; }}
    th {{ background: #333; color: white; padding: 12px; text-align: left; }}
    td {{ padding: 12px; border-bottom: 1px solid #eee; vertical-align: top; }}
    tr:hover {{ background: #f5f5f5; }}
    .avg-box {{ display:inline-block; background:white; border-radius:8px; padding:16px 28px; margin:8px; box-shadow:0 1px 4px rgba(0,0,0,0.12); text-align:center; }}
    .avg-box .label {{ font-size:12px; color:#888; margin-bottom:4px; }}
    .avg-box .val {{ font-size:28px; font-weight:bold; }}
  </style>
</head>
<body>
  <h1>RAGAs Evaluation Report</h1>
  <div class="summary">
    Dataset: <strong>HALLUCINATION_SET</strong> &nbsp;|&nbsp;
    {len(rows)} examples &nbsp;|&nbsp;
    5 answerable &nbsp;+&nbsp; 5 unanswerable
  </div>

  <h2>Dataset Averages</h2>
  <div>
    <div class="avg-box">
      <div class="label">Faithfulness</div>
      <div class="val" style="color:{'#2ecc71' if avg_f >= 0.8 else '#e74c3c'}">{avg_f:.2f}</div>
      <div style="font-size:11px;color:#aaa;margin-top:4px">stays in context?</div>
    </div>
    <div class="avg-box">
      <div class="label">AnswerRelevancy</div>
      <div class="val" style="color:{'#2ecc71' if avg_a >= 0.7 else '#e74c3c'}">{avg_a:.2f}</div>
      <div style="font-size:11px;color:#aaa;margin-top:4px">addresses the question?</div>
    </div>
    <div class="avg-box">
      <div class="label">ContextRecall</div>
      <div class="val" style="color:{'#2ecc71' if avg_c >= 0.7 else '#e74c3c'}">{avg_c:.2f}</div>
      <div style="font-size:11px;color:#aaa;margin-top:4px">context sufficient?</div>
    </div>
  </div>

  <h2>Results</h2>
  <p style="color:#555;font-size:14px">
    <strong style="color:#3498db">Answerable</strong> — the resume contains the answer. Model must stay faithful.<br>
    <strong style="color:#9b59b6">Unanswerable</strong> — the resume does not contain the answer. Model must say "not mentioned".
  </p>
  <table>
    <tr>
      <th>Type</th>
      <th>Question</th>
      <th>Model Response</th>
      <th>Expected</th>
      <th>Faithfulness</th>
      <th>AnswerRelevancy</th>
      <th>ContextRecall</th>
    </tr>
    {table_rows}
  </table>

  <h2>Metric Guide</h2>
  <table style="width:700px">
    <tr><th>Metric</th><th>What it measures</th><th>How</th><th>Good score</th></tr>
    <tr><td>Faithfulness</td><td>Are model claims supported by context?</td><td>LLM decomposes answer into claims, checks each against context</td><td>&gt;0.8</td></tr>
    <tr><td>AnswerRelevancy</td><td>Does the answer address the question?</td><td>Embeddings — semantic similarity between question and answer</td><td>&gt;0.7</td></tr>
    <tr><td>ContextRecall</td><td>Does context contain enough to answer?</td><td>LLM decomposes reference into claims, checks which are in context</td><td>&gt;0.7</td></tr>
  </table>
</body>
</html>"""

    report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ragas_report.html"))
    with open(report_path, "w") as f:
        f.write(html)
    webbrowser.open(f"file://{report_path}")
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    run_evaluation()
