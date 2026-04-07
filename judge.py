from typing import Optional

from deepeval.models.base_model import DeepEvalBaseLLM
from config import client, JUDGE_MODEL_NAME


class ClaudeJudge(DeepEvalBaseLLM):
    def __init__(self, model_name: str = JUDGE_MODEL_NAME, system_prompt: Optional[str] = None):
        self.model_name = model_name
        self.system_prompt = system_prompt

    def load_model(self):
        return self.model_name

    def generate(self, prompt: str) -> str:
        kwargs = dict(
            model=self.model_name,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        if self.system_prompt:
            kwargs["system"] = self.system_prompt
        message = client.messages.create(**kwargs)
        return message.content[0].text

    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)

    def get_model_name(self) -> str:
        return self.model_name


class LinguistJudge(ClaudeJudge):
    def __init__(self):
        super().__init__(system_prompt=(
            "You are an elementary school student. Score responses based on whether "
            "you can understand them easily. Give low scores to answers that use big "
            "words, technical terms, long sentences, or complicated explanations. "
            "Give high scores only to answers that are short, simple, and easy for "
            "a young child to understand."
        ))

    def get_model_name(self) -> str:
        return "ElementaryStudentJudge"


class FactCheckerJudge(ClaudeJudge):
    def __init__(self):
        super().__init__(system_prompt=(
            "You are a fact-checker. Score responses based solely on whether the "
            "core fact is present in the answer. Ignore grammar, tone, and extra "
            "detail entirely — only check if the key factual answer is there."
        ))

    def get_model_name(self) -> str:
        return "FactCheckerJudge"
