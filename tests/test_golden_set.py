import json

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, GEval

from datasets.golden_set import GOLDEN_SET, STRUCTURED_SET
from rag.hallucination_set import HALLUCINATION_SET
from model import generate
from judge import ClaudeJudge, LinguistJudge, FactCheckerJudge
from similarity import compute as semantic_similarity

HAPPY_PATH = [e for e in GOLDEN_SET if e["category"] == "happy_path"]
METRIC_THRESHOLD = 0.7


@pytest.mark.parametrize("example", GOLDEN_SET)
def test_model_on_golden_set(example, report_results):
    judge = ClaudeJudge()
    # Lower threshold for a general assistant — it intentionally adds context beyond the question
    answer_relevancy = AnswerRelevancyMetric(threshold=0.5, model=judge)
    faithfulness = FaithfulnessMetric(threshold=METRIC_THRESHOLD, model=judge)
    correctness = GEval(
        name="Correctness",
        criteria="Determine whether the actual output is factually correct compared to the expected output.",
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        threshold=METRIC_THRESHOLD,
        verbose_mode=True,
        model=judge,
    )

    actual_output = generate(example["input"])
    sim_score = semantic_similarity(actual_output, example["expected_output"])

    test_case = LLMTestCase(
        input=example["input"],
        actual_output=actual_output,
        expected_output=example["expected_output"],
        retrieval_context=example["context"] if example["context"] else None,
    )

    metrics = [answer_relevancy, correctness]
    if example["context"]:
        metrics.append(faithfulness)

    print(f"\n[{example['category']}] {example['input'][:60]}")
    print(f"  SemanticSimilarity: {sim_score:.2f}")
    for m in metrics:
        m.measure(test_case)
        print(f"  {m.__class__.__name__}: {m.score:.2f} ({'PASS' if m.is_successful() else 'FAIL'})")

    report_results.append({
        "category": example["category"],
        "input": example["input"],
        "actual_output": actual_output,
        "expected_output": example["expected_output"],
        "scores": [(m.__class__.__name__, m.score, m.is_successful()) for m in metrics],
        "similarity": sim_score,
        "passed": all(m.is_successful() for m in metrics),
    })

    assert_test(test_case, metrics)


@pytest.mark.parametrize("example", HAPPY_PATH)
@pytest.mark.happy_path
def test_judge_personas(example, persona_results):
    actual_output = generate(example["input"])
    test_case = LLMTestCase(
        input=example["input"],
        actual_output=actual_output,
        expected_output=example["expected_output"],
    )

    scores = {}
    print(f"\n[persona] {example['input'][:60]}")
    for judge_cls in [LinguistJudge, FactCheckerJudge]:
        judge = judge_cls()
        metric = GEval(
            name="Correctness",
            criteria="Determine whether the actual output is factually correct compared to the expected output.",
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
            threshold=METRIC_THRESHOLD,
            model=judge,
        )
        metric.measure(test_case)
        scores[judge.get_model_name()] = (metric.score, metric.is_successful())
        print(f"  {judge.get_model_name()}: {metric.score:.2f} ({'PASS' if metric.is_successful() else 'FAIL'})")

    persona_results.append({
        "input": example["input"],
        "actual_output": actual_output,
        "expected_output": example["expected_output"],
        "scores": scores,
    })


@pytest.mark.parametrize("example", STRUCTURED_SET)
@pytest.mark.structured
def test_structured_output(example, structured_results):
    actual_output = generate(example["input"])
    print(f"\n[structured] {example['input'][:60]}")

    # Step 1: strip markdown code fences if present (LLMs often wrap JSON in ```json ... ```)
    cleaned = actual_output.strip()
    if cleaned.startswith("```"):
        cleaned = "\n".join(cleaned.split("\n")[1:])  # remove first line (```json)
        cleaned = cleaned.rstrip("`").strip()

    # Step 2: validate JSON — fail immediately if invalid
    try:
        parsed = json.loads(cleaned)
        json_valid = True
    except json.JSONDecodeError:
        json_valid = False
        parsed = None

    print(f"  JSON valid: {json_valid}")

    # Step 2: if valid, check all expected keys match
    key_matches = {}
    if json_valid and parsed:
        for key, expected_val in example["expected_json"].items():
            actual_val = parsed.get(key, "")
            match = bool(actual_val) if key == "definition" else str(actual_val).lower() == str(expected_val).lower()
            key_matches[key] = (actual_val, expected_val, match)
            print(f"  {key}: {actual_val!r} (expected {expected_val!r}) → {'✓' if match else '✗'}")

    passed = json_valid and all(v[2] for v in key_matches.values())

    structured_results.append({
        "input": example["input"],
        "actual_output": actual_output,
        "json_valid": json_valid,
        "key_matches": key_matches,
        "passed": passed,
    })

    assert json_valid, f"Model did not return valid JSON. Got: {actual_output}"
    assert all(v[2] for v in key_matches.values()), f"Key mismatches: {key_matches}"


@pytest.mark.parametrize("example", HALLUCINATION_SET)
@pytest.mark.hallucination
def test_hallucination(example, hallucination_results):
    judge = ClaudeJudge()
    faithfulness = FaithfulnessMetric(threshold=METRIC_THRESHOLD, model=judge)
    correctness = GEval(
        name="Correctness",
        criteria="Determine whether the actual output is factually correct compared to the expected output.",
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        threshold=METRIC_THRESHOLD,
        verbose_mode=True,
        model=judge,
    )

    context_text = "\n".join(example["context"])
    system_prompt = (
        "You are a helpful assistant answering questions based only on the provided document. "
        "If the document does not contain the answer, say so clearly — do not guess or invent information.\n\n"
        f"Document:\n{context_text}"
    )
    actual_output = generate(example["input"], system=system_prompt)
    sim_score = semantic_similarity(actual_output, example["expected_output"])

    test_case = LLMTestCase(
        input=example["input"],
        actual_output=actual_output,
        expected_output=example["expected_output"],
        retrieval_context=example["context"],
    )

    metrics = [faithfulness, correctness]

    answerable_label = "answerable" if example["answerable"] else "unanswerable"
    print(f"\n[hallucination/{answerable_label}] {example['input'][:60]}")
    print(f"  SemanticSimilarity: {sim_score:.2f}")
    for m in metrics:
        m.measure(test_case)
        print(f"  {m.__class__.__name__}: {m.score:.2f} ({'PASS' if m.is_successful() else 'FAIL'})")

    hallucination_results.append({
        "input": example["input"],
        "actual_output": actual_output,
        "expected_output": example["expected_output"],
        "answerable": example["answerable"],
        "scores": [(m.__class__.__name__, m.score, m.is_successful()) for m in metrics],
        "similarity": sim_score,
        "passed": all(m.is_successful() for m in metrics),
    })

    assert_test(test_case, metrics)
