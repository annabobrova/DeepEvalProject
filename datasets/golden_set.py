"""
Golden set: curated happy-path examples used as the model's baseline ground truth.

Each entry has:
  - input:           the user's question or prompt
  - expected_output: the ideal answer (ground truth)
  - context:         (optional) retrieved documents the model should use
  - category:        happy_path
"""

GOLDEN_SET = [
    {
        "category": "happy_path",
        "input": "What is the capital of France?",
        "expected_output": "The capital of France is Paris.",
        "context": [],
    },
    {
        "category": "happy_path",
        "input": "Explain what a large language model is in one sentence.",
        "expected_output": (
            "A large language model (LLM) is a deep learning model trained on massive "
            "amounts of text data to understand and generate human language."
        ),
        "context": [],
    },
    {
        "category": "happy_path",
        "input": "What is 2 + 2?",
        "expected_output": "2 + 2 equals 4.",
        "context": [],
    },
    {
        "category": "happy_path",
        "input": "Who wrote the play Hamlet?",
        "expected_output": "Hamlet was written by William Shakespeare.",
        "context": [],
    },
    {
        "category": "happy_path",
        "input": "What does RAG stand for in AI?",
        "expected_output": (
            "RAG stands for Retrieval-Augmented Generation, a technique that combines "
            "information retrieval with text generation to ground model responses in external knowledge."
        ),
        "context": [],
    },
]
