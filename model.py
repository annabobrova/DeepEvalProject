from config import client, MODEL_NAME


def generate(prompt: str, system: str = "You are a helpful assistant.") -> str:
    message = client.messages.create(
        model=MODEL_NAME,
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
