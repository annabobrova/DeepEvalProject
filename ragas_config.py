"""
ragas_config.py — RAGAs LLM and embeddings configuration.

RAGAs 0.4.x collections metrics require an InstructorLLM — a wrapper built on
the `instructor` library, which adds structured output support on top of standard
LLM clients. We create an Anthropic client pointed at OpenCode Zen (Anthropic-
compatible API) and wrap it with instructor, then pass it to InstructorLLM.

This file mirrors the role of judge.py for DeepEval:
  judge.py        → wraps backends.run() for DeepEval's LLMJudge
  ragas_config.py → wraps the Anthropic client for RAGAs' internal judge calls
"""

import json
import os

import anthropic
import instructor
from ragas.embeddings import HuggingFaceEmbeddings as RagasHFEmbeddings
from ragas.llms import InstructorLLM
from ragas.llms.base import InstructorModelArgs


def _load_opencode_api_key() -> str:
    """Read the OpenCode Zen API key — same logic as backends.py."""
    auth_path = os.path.expanduser("~/.local/share/opencode/auth.json")
    try:
        with open(auth_path) as f:
            data = json.load(f)
        return data["opencode"]["key"]
    except (FileNotFoundError, KeyError) as e:
        raise RuntimeError(
            f"OpenCode Zen API key not found in {auth_path}. "
            "Run 'opencode providers login' to authenticate."
        ) from e


def make_ragas_llm() -> InstructorLLM:
    """
    Build a RAGAs-compatible LLM wrapper.

    RAGAs 0.4.x collections metrics use InstructorLLM internally to get
    structured (typed) responses from the model. The chain is:

      InstructorLLM
        └─ instructor.from_anthropic(client)   ← adds structured output support
             └─ anthropic.Anthropic(base_url)  ← points at OpenCode Zen
                  └─ HTTP POST https://opencode.ai/zen/v1/messages
    """
    # AsyncAnthropic is required — RAGAs calls agenerate() internally (async pipeline)
    anthropic_client = anthropic.AsyncAnthropic(
        api_key=_load_opencode_api_key(),
        base_url="https://opencode.ai/zen",  # SDK appends /v1/messages automatically
    )
    instructor_client = instructor.from_anthropic(anthropic_client)
    return InstructorLLM(
        client=instructor_client,
        model="big-pickle",
        provider="anthropic",
        model_args=InstructorModelArgs(max_tokens=8192),
    )


def make_ragas_embeddings() -> RagasHFEmbeddings:
    """
    Build a RAGAs-compatible embeddings object.

    Used by AnswerRelevancy to compare the answer embedding against the
    question embedding (semantic similarity, not LLM-based).

    Uses RAGAs' own HuggingFaceEmbeddings class with all-MiniLM-L6-v2 —
    the same model as similarity.py, so no new model download is needed.
    """
    return RagasHFEmbeddings(model="all-MiniLM-L6-v2")
