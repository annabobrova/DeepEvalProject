import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.environ.get("MODEL_NAME", "claude-haiku-4-5-20251001")
JUDGE_MODEL_NAME = os.environ.get("JUDGE_MODEL_NAME", "claude-haiku-4-5-20251001")

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
