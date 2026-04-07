import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, GEval

from datasets.golden_set import GOLDEN_SET
from model import generate
from judge import ClaudeJudge, LinguistJudge, FactCheckerJudge

HAPPY_PATH = [e for e in GOLDEN_SET if e["category"] == "happy_path"]
METRIC_THRESHOLD = 0.7


@pytest.mark.parametrize("example", GOLDEN_SET)
def test_model_on_golden_set(example, report_results):
    judge = ClaudeJudge()
    answer_relevancy = AnswerRelevancyMetric(threshold=METRIC_THRESHOLD, model=judge)
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
    for m in metrics:
        m.measure(test_case)
        print(f"  {m.__class__.__name__}: {m.score:.2f} ({'PASS' if m.is_successful() else 'FAIL'})")

    report_results.append({
        "category": example["category"],
        "input": example["input"],
        "actual_output": actual_output,
        "expected_output": example["expected_output"],
        "scores": [(m.__class__.__name__, m.score, m.is_successful()) for m in metrics],
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
