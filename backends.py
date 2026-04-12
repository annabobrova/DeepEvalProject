import json
import os
import subprocess
import urllib.request

# Set via MODEL_BACKEND env var. Add new backend names here as they are supported.
MODEL_BACKEND = os.getenv("MODEL_BACKEND", "opencode_api")

_OPENCODE_ZEN_URL = "https://opencode.ai/zen/v1/messages"
_OPENCODE_ZEN_MODEL = os.getenv("OPENCODE_MODEL", "big-pickle")


def _env_without_api_key() -> dict:
    """Return the current environment with ANTHROPIC_API_KEY removed.
    This forces the CLI to use OAuth (subscription) instead of API credits.
    """
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    return env


def _run_claude(prompt: str, system: str, timeout: int) -> str:
    cmd = ["claude", "-p", prompt]
    if system:
        cmd += ["--system-prompt", system]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=timeout,
            env=_env_without_api_key(),
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"claude CLI timed out after {timeout}s")
    if result.returncode != 0:
        raise RuntimeError(
            f"claude CLI exited with code {result.returncode}. stderr: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def _run_opencode(prompt: str, system: str, timeout: int) -> str:
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    try:
        result = subprocess.run(
            ["opencode", "run", full_prompt, "--format", "json", "--agent", "general"],
            capture_output=True, text=True, timeout=timeout,
            env=_env_without_api_key(),
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"opencode CLI timed out after {timeout}s")
    if result.returncode != 0:
        raise RuntimeError(
            f"opencode exited with code {result.returncode}. stderr: {result.stderr.strip()}"
        )
    text_parts = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            if event.get("type") == "error":
                raise RuntimeError(f"opencode error event: {event}")
            if event.get("type") == "text":
                text_parts.append(event["part"]["text"])
        except (json.JSONDecodeError, KeyError):
            continue
    output = "".join(text_parts).strip()
    if not output:
        raise RuntimeError(
            f"opencode returned no text output. stdout: {result.stdout[:200]!r}"
        )
    return output


def _load_opencode_api_key() -> str:
    """Read the OpenCode Zen API key from ~/.local/share/opencode/auth.json."""
    auth_path = os.path.expanduser("~/.local/share/opencode/auth.json")
    try:
        with open(auth_path) as f:
            data = json.load(f)
        key = data["opencode"]["key"]
    except (FileNotFoundError, KeyError) as e:
        raise RuntimeError(
            f"OpenCode Zen API key not found in {auth_path}. "
            "Run 'opencode providers login' to authenticate."
        ) from e
    return key


def _run_opencode_api(prompt: str, system: str, timeout: int) -> str:
    """Call OpenCode Zen's Anthropic-compatible API directly — no CLI, no agent overhead."""
    api_key = _load_opencode_api_key()

    messages = [{"role": "user", "content": prompt}]
    body = {
        "model": _OPENCODE_ZEN_MODEL,
        "max_tokens": 4096,
        "messages": messages,
    }
    if system:
        body["system"] = system

    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        _OPENCODE_ZEN_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "User-Agent": "opencode/1.4.1",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            response = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        if e.code == 429:
            raise RuntimeError(
                f"OpenCode Zen rate limit exceeded. Wait a moment and retry. Details: {body_text}"
            ) from e
        raise RuntimeError(f"OpenCode Zen API error {e.code}: {body_text}") from e

    # Response may include thinking blocks before the text block — find the text one.
    try:
        text = next(
            block["text"] for block in response["content"] if block.get("type") == "text"
        )
        return text.strip()
    except StopIteration:
        raise RuntimeError(f"No text block in OpenCode Zen response: {response}")


# Registry — to add a new backend:
# 1. Write a _run_<name>(prompt, system, timeout) -> str function above
# 2. Add it to this dict
BACKENDS = {
    "claude": _run_claude,
    "opencode": _run_opencode,
    "opencode_api": _run_opencode_api,
}


def run(prompt: str, system: str, timeout: int) -> str:
    backend_fn = BACKENDS.get(MODEL_BACKEND)
    if backend_fn is None:
        raise ValueError(
            f"Unknown backend '{MODEL_BACKEND}'. Available: {list(BACKENDS)}"
        )
    return backend_fn(prompt, system, timeout)
