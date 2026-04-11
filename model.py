from backends import run as _backend_run

_DEFAULT_SYSTEM = (
    "You are a helpful assistant. Keep your answer brief — no more than 3-4 sentences. "
    "If the question is direct and has a clear answer, answer only what was asked and do not provide extra information."
)

_MODEL_TIMEOUT = 120


def generate(prompt: str, system: str = _DEFAULT_SYSTEM) -> str:
    return _backend_run(prompt, system, timeout=_MODEL_TIMEOUT)
