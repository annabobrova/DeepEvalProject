"""
Golden set: curated input/expected output pairs used to evaluate the model.

Each entry is a dict with:
  - input:          the user's question or prompt
  - expected_output: the ideal answer (ground truth)
  - context:        (optional) retrieved documents or background facts the model should use
"""

GOLDEN_SET = [
    {
        "input": "What is the capital of France?",
        "expected_output": "The capital of France is Paris.",
        "context": ["France is a country in Western Europe. Its capital city is Paris."],
    },
    {
        "input": "Explain what a large language model is in one sentence.",
        "expected_output": (
            "A large language model (LLM) is a deep learning model trained on massive "
            "amounts of text data to understand and generate human language."
        ),
        "context": [],
    },
    {
        "input": "What is 2 + 2?",
        "expected_output": "2 + 2 equals 4.",
        "context": [],
    },
    {
        "input": "Who wrote the play Hamlet?",
        "expected_output": "Hamlet was written by William Shakespeare.",
        "context": ["Hamlet is a tragedy written by William Shakespeare, likely between 1599 and 1601."],
    },
    {
        "input": "What does RAG stand for in AI?",
        "expected_output": (
            "RAG stands for Retrieval-Augmented Generation, a technique that combines "
            "information retrieval with text generation to ground model responses in external knowledge."
        ),
        "context": [
            "RAG (Retrieval-Augmented Generation) is an AI framework that retrieves relevant "
            "documents from a knowledge base before generating a response."
        ],
    },
]
