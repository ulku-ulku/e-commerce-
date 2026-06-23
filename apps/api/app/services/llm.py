"""Sağlayıcı-bağımsız LLM istemcisi (OpenAI-uyumlu chat/completions).

Tek bir HTTP arayüzü; LLM_BASE_URL ile herhangi bir OpenAI-uyumlu sağlayıcıya bağlanır.
Anahtar (LLM_API_KEY) yoksa çağıran taraf deterministik fallback'e düşer.
"""
import httpx

from app.core.config import settings


def available() -> bool:
    return bool(settings.LLM_API_KEY)


def chat(messages: list[dict], tools: list[dict] | None = None,
         max_tokens: int = 1024, temperature: float = 0.3) -> dict:
    """OpenAI-uyumlu chat completion. Ham 'message' nesnesini döndürür."""
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}", "Content-Type": "application/json"}
    body = {"model": settings.LLM_MODEL, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature}
    if tools:
        body["tools"] = tools
    with httpx.Client(timeout=60) as c:
        r = c.post(f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
                   headers=headers, json=body)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]
