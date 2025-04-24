import os
import sys
import asyncio
from typing import AsyncGenerator, Optional, List
from pathlib import Path

from .config import LLMConfig

# Add site-packages to path if it exists
site_packages = LLMConfig.get_site_packages_path()
if site_packages.exists():
    sys.path.insert(0, str(site_packages))

class OpenAIAdapter:
    """Adapter for OpenAI API with interface"""
    MAX_RETRIES = 3
    RETRY_DELAY = 1

    def __init__(self):
        try:
            from openai import OpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError, AuthenticationError
            
            api_key = os.getenv("OPENAI_API_KEY")
            
            if not api_key:
                raise ValueError("OpenAI API key not found in environment")
                
            self.client = OpenAI(api_key=api_key)
            self.error_types = {
                'APIError': APIError,
                'Connection': APIConnectionError,
                'RateLimit': RateLimitError,
                'Timeout': APITimeoutError,
                'Authentication': AuthenticationError
            }
            
        except ImportError as e:
            raise ImportError(f"Failed to import OpenAI: {str(e)}. Ensure openai>=1.25.0 is installed.")

    async def _make_request_with_retry(self, text: str, system_prompt: str) -> AsyncGenerator[str, None]:
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text}
                    ],
                    stream=False,
                )
                yield response.choices[0].message.content
                return
                
            except self.error_types['Connection'] as e:
                if attempt == self.MAX_RETRIES - 1:
                    yield f"Connection Error: Failed to reach OpenAI API after {self.MAX_RETRIES} attempts."
                    return
                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                
            except self.error_types['Authentication']:
                yield "Authentication Error: Invalid API key or API key not found in environment."
                return
                
            except self.error_types['RateLimit']:
                yield "Rate Limit Error: Too many requests."
                return
                
            except self.error_types['Timeout']:
                if attempt == self.MAX_RETRIES - 1:
                    yield f"Timeout Error: Request timed out after {self.MAX_RETRIES} attempts."
                    return
                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                
            except self.error_types['APIError'] as e:
                yield f"OpenAI API Error: {str(e)}"
                return
                
            except Exception as e:
                yield f"Unexpected error: {str(e)}"
                return

    async def generate(self, text: str, custom_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        if not text or not text.strip():
            yield "Please provide text for analysis."
            return
            
        system_prompt = custom_prompt or LLMConfig.SYSTEM_PROMPT
        async for token in self._make_request_with_retry(text, system_prompt):
            yield token

    async def generate_as_list(self, text: str, custom_prompt: Optional[str] = None) -> List[str]:
        return [token async for token in self.generate(text, custom_prompt)]