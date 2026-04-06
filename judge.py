from deepeval.models.base_model import DeepEvalBaseLLM
from config import client, JUDGE_MODEL_NAME


class ClaudeJudge(DeepEvalBaseLLM):
    def __init__(self, model_name: str = JUDGE_MODEL_NAME):
        self.model_name = model_name

    def load_model(self):
        return self.model_name

    def generate(self, prompt: str) -> str:
        message = client.messages.create(
            model=self.model_name,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)

    def get_model_name(self) -> str:
        return self.model_name
