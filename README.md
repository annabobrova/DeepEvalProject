# DeepEval Learning Project

A hands-on project for learning how to evaluate LLMs using [DeepEval](https://docs.confident-ai.com/).

## Project structure

```
DeepEvalProject/
├── datasets/
│   └── golden_set.py       # Curated input/expected-output pairs (ground truth)
├── tests/
│   └── test_golden_set.py  # Eval script: runs model + scores with DeepEval metrics
├── configs/
│   └── deepeval.ini        # DeepEval configuration (judge model, etc.)
├── model.py                # Anthropic API wrapper (the model under test)
├── requirements.txt
└── .env.example
```

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API keys
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY and OPENAI_API_KEY

# 3. (Optional) Log in to Confident AI for a visual dashboard
deepeval login
```

## Running evals

```bash
# Run all tests and see pass/fail per metric
deepeval test run tests/test_golden_set.py

# Or use pytest directly (no Confident AI upload)
pytest tests/test_golden_set.py -v
```

## Key concepts

| Concept | What it is |
|---|---|
| **Golden set** | Hand-curated examples with known correct answers — your ground truth |
| **Test case** | One (input, actual_output, expected_output, context) tuple |
| **Metric** | A scorer that judges one aspect of quality (relevancy, faithfulness, correctness) |
| **Threshold** | Minimum score (0–1) for a metric to pass |
| **Judge LLM** | A second LLM (usually GPT-4o) that scores the model's outputs |

## Metrics used

- **AnswerRelevancyMetric** — does the response actually answer the question?
- **FaithfulnessMetric** — does the response stay grounded in the provided context (no hallucination)?
- **GEval (Correctness)** — free-form correctness check against the expected output

## Next steps

- Add more examples to `datasets/golden_set.py`
- Try different metrics: `HallucinationMetric`, `BiasMetric`, `ToxicityMetric`
- Swap the model in `model.py` and compare scores
- Use `deepeval login` to track results over time in the Confident AI dashboard
