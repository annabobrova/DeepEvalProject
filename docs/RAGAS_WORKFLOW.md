# RAGAs Workflow — Recap Notes

A plain-language walkthrough of how this project uses RAGAs to evaluate an LLM against a resume document. Written for quick re-reading, not as formal docs.

---

## The goal

Test whether an LLM, when asked questions about a resume, **sticks to what the resume actually says** — or whether it invents facts. The whole project measures trustworthiness.

---

## The pieces

**The "document"** — `rag/documents/resume.py`
The resume, typed directly into a Python file as a list of 14 short strings. Each string is one pre-chunked fact (one line about skills, one about education, etc.). No PDF, no parsing — just a Python variable any other file can import.

**The test questions** — `rag/hallucination_set.py`
10 handwritten questions, each paired with the ideal answer:
- 5 **answerable** — resume contains the answer
- 5 **unanswerable** — resume does *not* contain the answer

The unanswerable ones are the real test: a good model should say *"the resume doesn't mention that"*; a bad model will make something up.

**The model under test** — called through `model.py` → `backends.py`
An LLM reached via a CLI or HTTP API. Send it a prompt, it returns text.

**The judge LLM** — configured in `ragas_config.py`
A *second* LLM that RAGAs calls internally to score answers. Uses the Anthropic SDK pointed at OpenCode Zen.

**The embedding model** — `all-MiniLM-L6-v2`
A small, local 87 MB model cached in `~/.cache/huggingface/`. Turns any sentence into a 384-number vector representing its meaning. Runs offline on CPU. Used for one metric only.

**The runner** — `ragas_eval.py`
Orchestrates everything and writes `ragas_report.html`.

---

## What happens when you run `python3.11 ragas_eval.py`

### Step 1 — ask the model 10 questions

For each of the 10 questions in `HALLUCINATION_SET`, the script:

1. Builds a system prompt: *"Answer only based on this document. If the answer isn't in it, say so."*
2. Pastes the **entire resume** into that system prompt. (No retrieval — the resume is small enough to fit in one prompt.)
3. Sends the question to the model.
4. Records the model's answer.

After this step there are 10 rows, each with: the question, the resume chunks, the ideal answer, the model's actual answer, and whether the question was answerable.

### Step 2 — score each answer with three RAGAs metrics

RAGAs runs each metric across all 10 rows. Each metric looks at *different* inputs because they measure different things.

**Faithfulness** — *"Did the model only say things supported by the resume?"*
- The judge LLM reads the model's answer, breaks it into small factual claims, checks each claim against the resume.
- High score = no hallucination. Low = model invented facts.
- Inputs: question, answer, resume.

**AnswerRelevancy** — *"Did the answer actually address the question?"*
- No LLM. Uses the local **embedding** model.
- Turns the question into a 384-number vector, turns the answer into a 384-number vector, measures how close they are (cosine similarity).
- High score = answer is about the same thing as the question. Low = off-topic.
- Inputs: question, answer only. (Resume isn't needed — purely question-vs-answer.)

**ContextRecall** — *"Does the resume contain enough information to answer well?"*
- The judge LLM reads the *ideal* answer (not the model's answer), breaks it into claims, checks which of those claims appear in the resume.
- High score = the document has enough to answer. Low = key info is missing from the resume.
- Inputs: question, resume, ideal answer.

Each metric returns a number 0–1 per question.

### Step 3 — write the report

The script:
- Prints a grid of scores to the terminal
- Computes averages across all 10 questions for each metric
- Writes `ragas_report.html` with a color-coded table (green ≥0.8, orange ≥0.6, red below)
- Opens the report in the browser

---

## The flow as one picture

```
resume.py ──┐
            ├──► model prompt ──► LLM under test ──► model answer ──┐
question ───┘                                                        │
                                                                     ▼
                                                               RAGAs metrics
                                                                     │
          ┌──────────────────────┬──────────────────────┐            │
          ▼                      ▼                      ▼            │
     Faithfulness         AnswerRelevancy         ContextRecall      │
     (judge LLM checks    (embeddings compare     (judge LLM checks  │
     answer claims         question vector to     ideal-answer claims│
     against resume)       answer vector)         against resume)    │
          │                      │                      │            │
          └──────────────────────┴──────────────────────┘            │
                                 │                                   │
                                 ▼                                   │
                         ragas_report.html ◄──────────────────────── ┘
```

---

## The three "models" at work (keep these straight)

1. **Model under test** — gets the question + resume, writes an answer. This is what you're evaluating.
2. **Judge LLM** (inside RAGAs) — scores Faithfulness and ContextRecall by decomposing claims.
3. **Embedding model** (local, not an LLM — just a vector maker) — scores AnswerRelevancy without any LLM call.

Every run makes: **10 model calls + ~20 judge LLM calls + 20 embedding computations**. Embeddings are instant; judge calls are the slow part.

---

## Key concepts to remember

### Embeddings
A vector of numbers (here, 384 of them) that represents the *meaning* of a piece of text. Texts with similar meaning produce vectors that point in similar directions; unrelated texts point in different directions. **Cosine similarity** measures how close two vectors are (1.0 = identical meaning, 0 = unrelated).

### `all-MiniLM-L6-v2`
- Small distilled BERT-based model from HuggingFace (~22M parameters, 87 MB).
- Max input ~256 tokens. Output: 384-dim vector.
- Runs locally on CPU in milliseconds. Downloaded once, cached in `~/.cache/huggingface/`, then fully offline.

### "Cache"
A local copy of something downloaded from the internet, saved so it doesn't need to be downloaded again. Lives in `~/.cache/` by Unix convention. Safe to delete — re-downloads on next use.

### Chunking
Splitting a document into small passages so each piece can be embedded, retrieved, or passed to a model independently. In this project the resume is chunked by hand (each Python list entry is one chunk). In production you'd have a function that splits a PDF into ~200-word chunks programmatically.

### Vector database
A database built to answer *"find the K items whose vectors are closest to this one"* quickly. Examples: Chroma, Pinecone, Weaviate, pgvector. Regular SQL databases can't do this efficiently at scale.

---

## What's deliberately simplified

- **No vector database.** The resume is small enough to paste whole into every prompt. A production RAG pipeline with a 10,000-page document would embed the chunks, store them in a vector DB, and retrieve only the top-k relevant chunks per question. This project skips retrieval entirely.
- **No chunking code.** The resume is pre-chunked by hand. A real pipeline would split a PDF programmatically.
- **Small dataset.** 10 questions is enough to see the metrics work; a real eval suite would have hundreds.

---

## Why a vector DB would be needed at real scale

A 1-page resume fits in one prompt. A 10,000-page handbook doesn't — two hard limits:

1. **Context window** — even Claude's 1M-token window can't fit Wikipedia. Stuffing irrelevant text also hurts answer quality.
2. **Cost and speed** — every token costs money and time. Sending 500K tokens per question is wasteful when only 5 paragraphs are relevant.

**Production flow with a vector DB:**

*Indexing (once):* split handbook into 10,000 chunks → embed each chunk → store vectors in the DB.

*At query time (per question):* embed the question → ask the DB for the 5 closest chunks → paste only those into the prompt → LLM answers based on just that context.

The vector DB is a **semantic search engine** — it matches meaning, not keywords. "How many days off" still finds the "vacation policy" chunk even though the words don't overlap.

---

## One-liner for explaining the project

*"I evaluate an LLM by asking it 10 questions about my resume — half are answerable, half aren't. A second LLM (the judge) and a local embedding model score the responses on three RAGAs metrics: does the model stay faithful to the resume, does it actually answer the question, and is there enough context to answer well. Results go into an HTML report. The whole thing is a simplified RAG pipeline — I skip the vector-DB retrieval step because my document is small enough to fit in one prompt."*
