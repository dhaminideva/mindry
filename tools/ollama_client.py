"""
tools/ollama_client.py
Lightweight async Ollama client — auto-detects installed model.
"""
import os
import json
import httpx
import structlog

log = structlog.get_logger()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_PREFERRED_MODELS = ["llama3.2", "llama3.1", "llama3", "llama2", "mistral", "phi3", "gemma2", "gemma", "qwen2"]
_detected_model: str | None = None


async def get_model() -> str:
    global _detected_model
    if _detected_model:
        return _detected_model
    env_model = os.getenv("LLM_MODEL", "")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            installed = [m["name"].split(":")[0] for m in data.get("models", [])]
            installed_full = [m["name"] for m in data.get("models", [])]
            log.info("ollama_models_found", models=installed_full)
            if env_model:
                # Match even if tag is missing, e.g. "llama3.2" matches "llama3.2:1b"
                match = next((n for n in installed_full if n.startswith(env_model)), None)
                if match:
                    _detected_model = match
                    log.info("ollama_using_model", model=_detected_model, source="env")
                    return _detected_model
            for preferred in _PREFERRED_MODELS:
                if preferred in installed:
                    full = next(n for n in installed_full if n.startswith(preferred))
                    _detected_model = full
                    log.info("ollama_using_model", model=_detected_model, source="auto-detect")
                    return _detected_model
            if installed_full:
                _detected_model = installed_full[0]
                log.info("ollama_using_model", model=_detected_model, source="fallback")
                return _detected_model
            raise RuntimeError("No models installed in Ollama. Run: ollama pull llama3.2")
    except httpx.ConnectError:
        raise RuntimeError(
            "Cannot reach Ollama at http://localhost:11434. "
            "Check your system tray or run 'ollama serve' in a terminal."
        )


async def chat(system_prompt: str, user_message: str) -> str:
    model = await get_model()
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"]


def parse_json_response(raw: str) -> dict | list:
    text = raw.strip()

    # Strip markdown fences
    if "```" in text:
        start = text.find("```")
        end = text.rfind("```")
        inner = text[start+3:end].strip()
        if inner.startswith("json"):
            inner = inner[4:].strip()
        text = inner

    # Find the first { or [ and last } or ]
    start_chars = [i for i, c in enumerate(text) if c in ('{', '[')]
    end_chars   = [i for i, c in enumerate(text) if c in ('}', ']')]
    if not start_chars or not end_chars:
        raise ValueError(f"No JSON found in response: {text[:200]}")
    text = text[start_chars[0]:end_chars[-1]+1]

    # Fix common LLM JSON mistakes
    import re
    text = re.sub(r',\s*}', '}', text)   # trailing comma in object
    text = re.sub(r',\s*]', ']', text)   # trailing comma in array
    text = re.sub(r'[\x00-\x1f\x7f]', ' ', text)  # control characters

    return json.loads(text)