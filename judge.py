from typing import Optional

from deepeval.models.base_model import DeepEvalBaseLLM
from config import JUDGE_MODEL_NAME
from backends import run as _backend_run

_JUDGE_TIMEOUT = 300  # Judge prompts are longer than model prompts — allow more time


class LLMJudge(DeepEvalBaseLLM):
    def __init__(
        self, model_name: str = JUDGE_MODEL_NAME, system_prompt: Optional[str] = None
    ):
        self.model_name = model_name
        self.system_prompt = system_prompt

    def load_model(self):
        return self.model_name

    def generate(self, prompt: str) -> str:
        output = _backend_run(prompt, self.system_prompt or "", timeout=_JUDGE_TIMEOUT)
        # Strip markdown code fences — some backends wrap JSON responses in ```json ... ```
        if output.startswith("```"):
            lines = output.split("\n")
            output = "\n".join(lines[1:]).rstrip("`").strip()
        return output

    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)

    def get_model_name(self) -> str:
        return self.model_name
