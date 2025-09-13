import requests
from .normalizer import sanitize_llm_output


def query_llm(api_url: str, model_name: str, messages, *,
              temperature: float = 0.0, top_p: float = 0.1,
              max_tokens: int = 1500,
              presence_penalty: float = 0.0, frequency_penalty: float = 0.0,
              timeout: int = 180) -> str:
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
        "max_tokens": max_tokens,
    }
    resp = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return sanitize_llm_output(content)

