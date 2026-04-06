# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies** (requires Python 3.10+):
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

This project evaluates an LLM (model under test) using DeepEval metrics, scored by a second LLM acting as a judge.

**Flow:**
```
Input → model.py (Claude Haiku) → actual_output
                                        ↓
expected_output ──────────→ judge.py (ClaudeJudge) → score + reason
```

**Key files and their roles:**
- `config.py` — single source of truth for the shared Anthropic client and model names. Both `model.py` and `judge.py` import from here. Model names can be overridden via `MODEL_NAME` / `JUDGE_MODEL_NAME` env vars.
- `model.py` — thin wrapper around the Anthropic API; `generate(prompt)` is the only function.
- `judge.py` — `ClaudeJudge` subclasses `DeepEvalBaseLLM` to plug Claude into DeepEval's metric scoring pipeline.
- `datasets/golden_set.py` — the ground truth dataset. Each entry has `input`, `expected_output`, and optional `context` (used for `FaithfulnessMetric`).
- `tests/test_golden_set.py` — parameterized pytest tests, one per golden set entry. Metrics are instantiated fresh per test to avoid stale state. Generates `report.html` via `pytest_sessionfinish`.

**Metrics used:**
- `AnswerRelevancyMetric` — does the response address the question?
- `GEval (Correctness)` — factual correctness vs. expected output (applied to all examples)
- `FaithfulnessMetric` — no hallucination beyond provided context (only applied when `context` is non-empty)

**Environment:**
Requires a `.env` file (copy from `.env.example`):
```
ANTHROPIC_API_KEY=...
MODEL_NAME=claude-haiku-4-5-20251001       # optional override
JUDGE_MODEL_NAME=claude-haiku-4-5-20251001 # optional override
```
