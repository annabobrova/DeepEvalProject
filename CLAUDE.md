# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important Rules

- **Always run tests with report generation.** Never run tests without the full `pytest_sessionfinish` report pipeline. Use the commands below as-is — do not add flags that suppress output or skip session teardown.
- **New tests must appear in the report.** Any new test added to `tests/test_golden_set.py` must also produce output in `report.html`. Add the result to the appropriate session-scoped list in `conftest.py` and render it in `pytest_sessionfinish`. For RAGAs tests, results must appear in `ragas_report.html`.
- **Always update README.md after code changes.** Any change to architecture, file structure, backends, metrics, or test design must be reflected in README.md before the task is considered done.
- **Speak up if a requested approach is not the best solution.** If a better alternative exists, say so before implementing.
- **Keep the project simple and easy to read.** Push back on any change that adds complexity without clear necessity. This project is a learning tool — clarity matters more than completeness.

## Commands

**Install dependencies** (requires Python 3.11+):
```bash
pip3.11 install -r requirements.txt
```

**Run all eval tests + generate report.html:**
```bash
python3.11 -m pytest tests/test_golden_set.py -v -s
```

**Run a single test case by index:**
```bash
python3.11 -m pytest "tests/test_golden_set.py::test_model_on_golden_set[example0]" -v -s
```

## Architecture

This project evaluates an LLM (model under test) using DeepEval metrics, scored by a second LLM acting as a judge. Both the model and judge call the CLI via subprocess — no direct API calls are made.

**Flow:**
```
Input → model.py (OpenCode CLI) → actual_output
                                        ↓
expected_output ──────────→ judge.py (LLMJudge / OpenCode CLI) → score + reason
```

**Key files and their roles:**
- `config.py` — display labels for the HTML report (`MODEL_NAME`, `JUDGE_MODEL_NAME`). Does not control which model is called.
- `backends.py` — backend registry. Add a new backend here (function + one dict entry) without touching any other file.
- `model.py` — `generate(prompt, system)` calls `backends.run()` with the model timeout.
- `judge.py` — `LLMJudge` subclasses `DeepEvalBaseLLM` and calls `backends.run()` with the judge timeout.
- `datasets/golden_set.py` — happy path ground truth (5 examples).
- `datasets/regression_set.py` — `REGRESSION_SET` (edge_case, negative, ambiguous, robustness), `TECHNICAL_SET` (persona tests), and `STRUCTURED_SET` (JSON output tests).
- `tests/test_golden_set.py` — parameterized pytest tests. Generates `report.html` via `pytest_sessionfinish`.

**Metrics used:**
- `AnswerRelevancyMetric` — does the response address the question? (skipped for negative/ambiguous categories)
- `GEval (Correctness)` — factual correctness vs. expected output
- `GEval (Simplicity)` — child-friendly language (persona tests only)
- `GEval (FactualCompleteness)` — precise and complete answer (persona tests only)
- `FaithfulnessMetric` — no hallucination beyond provided context

**Environment:**
Optional `.env` overrides:
```
MODEL_BACKEND=opencode_api      # default; "claude" to use Claude Code CLI via subscription OAuth
MODEL_NAME=claude               # display label only
JUDGE_MODEL_NAME=claude         # display label only
```
