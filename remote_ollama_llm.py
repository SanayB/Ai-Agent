from langchain_core.language_models.llms import LLM
from typing import Optional, List
import requests


class RemoteOllamaLLM(LLM):
    base_url: str
    model: str = "gemma:3b"
    temperature: float = 0.3

    @property
    def _llm_type(self) -> str:
        return "remote_ollama"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": self.temperature,
            "stream": False
        }
        if stop:
            payload["stop"] = stop

        try:
            response = requests.post(f"{self.base_url.rstrip('/')}/api/generate", json=payload)
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception as e:
            print(f"[ERROR] Remote Ollama call failed: {e}")
            return f"[ERROR] {str(e)}"
 