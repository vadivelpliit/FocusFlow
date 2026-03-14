import os
from typing import Optional

# Lazy imports for the provider in use
_gemini_client: Optional[object] = None
_openai_client: Optional[object] = None
_provider: Optional[str] = None  # "gemini" or "openai"


def _get_provider() -> str:
    global _provider
    if _provider is not None:
        return _provider
    if os.getenv("GEMINI_API_KEY"):
        _provider = "gemini"
        return "gemini"
    if os.getenv("OPENAI_API_KEY"):
        _provider = "openai"
        return "openai"
    raise ValueError(
        "Set either GEMINI_API_KEY or OPENAI_API_KEY in the environment."
    )


def complete(prompt: str, *, max_tokens: int = 2000, json_mode: bool = False) -> str:
    provider = _get_provider()
    if provider == "gemini":
        return _complete_gemini(prompt, max_tokens=max_tokens, json_mode=json_mode)
    return _complete_openai(prompt, max_tokens=max_tokens)


def _complete_gemini(prompt: str, *, max_tokens: int = 2000, json_mode: bool = False) -> str:
    global _gemini_client
    from google import genai
    from google.genai import types

    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        _gemini_client = genai.Client(api_key=api_key)
    client = _gemini_client
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    config_kw: dict = {
        "max_output_tokens": max_tokens,
        "temperature": 0.3,
    }
    if json_mode:
        config_kw["response_mime_type"] = "application/json"
    config = types.GenerateContentConfig(**config_kw)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    if not response:
        raise ValueError("Empty response from LLM")
    out = (response.text or "").strip()
    if not out:
        raise ValueError("Empty response from LLM (no or whitespace-only content)")
    return out


def _complete_openai(prompt: str, *, max_tokens: int = 2000) -> str:
    global _openai_client
    from openai import OpenAI

    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        _openai_client = OpenAI(api_key=api_key)
    client = _openai_client
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    if not response.choices:
        raise ValueError("Empty response from LLM")
    out = (response.choices[0].message.content or "").strip()
    if not out:
        raise ValueError("Empty response from LLM (no or whitespace-only content)")
    return out


def get_configured_provider() -> Optional[str]:
    """Return which provider will be used ('gemini' or 'openai'), or None if neither key is set."""
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return None
