import os
from dotenv import load_dotenv

load_dotenv()

# Display labels used in the HTML report and DeepEval output.
# These do not control which model is called — the backend is set via MODEL_BACKEND in model.py.
MODEL_NAME = os.environ.get("MODEL_NAME", "opencode")
JUDGE_MODEL_NAME = os.environ.get("JUDGE_MODEL_NAME", "opencode")
