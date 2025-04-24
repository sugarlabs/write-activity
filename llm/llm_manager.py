import sys
import os
from typing import AsyncGenerator, List, Optional
from pathlib import Path

from . import setup
from .config import LLMConfig

# Add site-packages to sys.path if it exists
if (site_packages := LLMConfig.get_site_packages_path()).exists():
    sys.path.insert(0, str(site_packages))


class LLMManager:
    def __init__(self):
        self._clients = {}
        self._backend_type = None
        self._initialized = False

    def initialize(self, backend_type: Optional[str] = None) -> bool:
        if self._initialized and backend_type == self._backend_type:
            return True

        self._backend_type = backend_type or LLMConfig.BACKEND_TYPE
        if not setup.init():
            return False

        if not LLMConfig.validate_config():
            return False

        try:
            self._initialize_backend()
            self._initialized = True
            return True
        except Exception as e:
            print(f"Initialization error: {e}")
            return False

    def _initialize_backend(self):
        backend = self._backend_type

        if backend == "qwen":
            from .qwen import LanguageModel
            self._clients["qwen"] = self._clients.get("qwen") or LanguageModel()

        elif backend == "openai":
            from .openai import OpenAIAdapter
            key = LLMConfig.get_api_key("openai")
            if not key:
                raise ValueError("OpenAI API key not found. Please ensure OPENAI_API_KEY is set in environment")
            self._clients["openai"] = self._clients.get("openai") or OpenAIAdapter()

        elif backend == "llama":
            from .llama import LlamaAdapter
            key = LLMConfig.get_api_key("llama")
            if not key:
                raise ValueError("Groq API key not found. Please ensure GROQ_API_KEY is set in environment")
            self._clients["llama"] = self._clients.get("llama") or LlamaAdapter()

        else:
            raise ValueError(f"Invalid backend type: {backend}")

    async def get_feedback(self, text: str, prompt_type: Optional[str] = None) -> AsyncGenerator[str, None]:
        if not self._initialized and not self.initialize():
            yield "Error: Failed to initialize model. Please check your configuration and API keys."
            return

        try:
            async for token in self._generate_response(text):
                yield token
        except Exception as e:
            yield f"Error: {e}"

    async def get_feedback_as_list(self, text: str, prompt_type: Optional[str] = None) -> List[str]:
        return [token async for token in self.get_feedback(text, prompt_type)]

    async def _generate_response(self, user_text: str) -> AsyncGenerator[str, None]:
        system_prompt = LLMConfig.SYSTEM_PROMPT
        backend = self._backend_type

        if backend not in self._clients:
            yield f"Error: {backend} client not initialized"
            return

        try:
            async for token in self._clients[backend].generate(user_text, system_prompt):
                yield token
        except Exception as e:
            yield f"Error generating response: {e}"
