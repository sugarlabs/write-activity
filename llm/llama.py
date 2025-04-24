import os
from typing import AsyncGenerator
from groq import Groq
from .config import LLMConfig

class LlamaAdapter:
    def __init__(self):
        self.api_key = LLMConfig.get_api_key("llama")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not set in environment")
        self.client = Groq(api_key=self.api_key)
        
    async def generate(self, user_text: str, system_prompt: str) -> AsyncGenerator[str, None]:
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ]
            
            response = self.client.chat.completions.create(
                messages=messages,
                model="llama3-8b-8192",
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"Error in Llama generation: {str(e)}" 