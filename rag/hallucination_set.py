"""
Hallucination test cases using the resume as the RAG context document.

Each entry has:
  - input:           question to ask the model
  - expected_output: ideal answer grounded in the resume
  - context:         the resume chunks (retrieved documents)
  - category:        "hallucination"
  - answerable:      True if the resume contains the answer, False if it does not

The key test: for unanswerable questions, the model must say "not mentioned"
instead of hallucinating a confident wrong answer.
"""

from rag.documents.resume import RESUME_CONTEXT

HALLUCINATION_SET = [
    # ------------------------------------------------------------------
    # Answerable — resume contains the answer, model must stay faithful
    # ------------------------------------------------------------------
    {
        "category": "hallucination",
        "answerable": True,
        "input": "What programming languages does the candidate know?",
        "expected_output": "According to the resume, the candidate knows Python, Java, TypeScript, and SQL.",
        "context": RESUME_CONTEXT,
    },
    {
        "category": "hallucination",
        "answerable": True,
        "input": "What is the candidate's most recent employer and role?",
        "expected_output": "The candidate's most recent role was Senior QA Automation Software Engineer at Charles River Associates (CRA), from January 2020 to September 2025.",
        "context": RESUME_CONTEXT,
    },
    {
        "category": "hallucination",
        "answerable": True,
        "input": "What certifications does the candidate hold?",
        "expected_output": "The candidate holds four certifications: AI Tester (December 2025), STQB Foundation Level (2024), Claude Code in Action (April 2026), and LFS158 Introduction to Kubernetes from the Linux Foundation (January 2026).",
        "context": RESUME_CONTEXT,
    },
    {
        "category": "hallucination",
        "answerable": True,
        "input": "How many years of QA experience does the candidate have?",
        "expected_output": "The candidate has 20+ years of QA automation experience.",
        "context": RESUME_CONTEXT,
    },
    {
        "category": "hallucination",
        "answerable": True,
        "input": "Where did the candidate complete their education?",
        "expected_output": "The candidate holds a Master of Science in Mathematics and Computer Science from Saint-Petersburg State University, Russia, earned in 1997.",
        "context": RESUME_CONTEXT,
    },

    # ------------------------------------------------------------------
    # Unanswerable — resume does NOT contain the answer, model must not hallucinate
    # ------------------------------------------------------------------
    {
        "category": "hallucination",
        "answerable": False,
        "input": "What is the candidate's salary expectation?",
        "expected_output": "The resume does not mention the candidate's salary expectation.",
        "context": RESUME_CONTEXT,
    },
    {
        "category": "hallucination",
        "answerable": False,
        "input": "Does the candidate have AWS experience?",
        "expected_output": "The resume does not mention AWS experience.",
        "context": RESUME_CONTEXT,
    },
    {
        "category": "hallucination",
        "answerable": False,
        "input": "Is the candidate available for full-time or contract work?",
        "expected_output": "The resume does not mention the candidate's availability or preferred work arrangement.",
        "context": RESUME_CONTEXT,
    },
    {
        "category": "hallucination",
        "answerable": False,
        "input": "Does the candidate have React or frontend development experience?",
        "expected_output": "The resume does not mention React or frontend development experience.",
        "context": RESUME_CONTEXT,
    },
    {
        "category": "hallucination",
        "answerable": False,
        "input": "What was the candidate's undergraduate degree?",
        "expected_output": "The resume does not mention an undergraduate degree. Only a Master of Science degree is listed.",
        "context": RESUME_CONTEXT,
    },
]
