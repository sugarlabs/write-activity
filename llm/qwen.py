import os
import torch
import asyncio
import logging
from typing import Optional, AsyncGenerator
from transformers import AutoTokenizer, AutoModelForCausalLM
from .config import LLMConfig

logger = logging.getLogger(__name__)

class LanguageModel:
    _model = None
    _tokenizer = None

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        self._load()

    def _load(self):
        if LanguageModel._model and LanguageModel._tokenizer:
            self.model = LanguageModel._model
            self.tokenizer = LanguageModel._tokenizer
            return

        os.environ["TRANSFORMERS_CACHE"] = str(LLMConfig.MODEL_CACHE_DIR)
        LLMConfig.MODEL_CACHE_DIR.mkdir(exist_ok=True)

        logger.info(f"Loading model: {LLMConfig.MODEL_NAME}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            LLMConfig.MODEL_NAME,
            trust_remote_code=True,
            use_fast=True,
            cache_dir=LLMConfig.MODEL_CACHE_DIR
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            LLMConfig.MODEL_NAME,
            device_map="auto",
            torch_dtype=self.dtype,
            trust_remote_code=True,
            cache_dir=LLMConfig.MODEL_CACHE_DIR,
            low_cpu_mem_usage=True
        ).eval()

        LanguageModel._model = self.model
        LanguageModel._tokenizer = self.tokenizer
        logger.info("Model loaded.")

    async def generate(self, text: str, prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        if not text.strip():
            yield "Please provide some text."
            return

        if len(text) > 1000:
            text = text[:1000] + "..."

        system_prompt = prompt or LLMConfig.SYSTEM_PROMPT
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]

        try:
            inputs = self.tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt"
            ).to(self.model.device)

            attention_mask = (inputs != self.tokenizer.pad_token_id).long().to(self.model.device)

            with torch.no_grad():
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.model.generate(
                        inputs,
                        attention_mask=attention_mask,
                        max_new_tokens=LLMConfig.MODEL_PARAMS["max_new_tokens"],
                        do_sample=True,
                        temperature=LLMConfig.MODEL_PARAMS["temperature"],
                        top_p=LLMConfig.MODEL_PARAMS["top_p"],
                        pad_token_id=self.tokenizer.pad_token_id,
                        eos_token_id=self.tokenizer.eos_token_id,
                        return_dict_in_generate=True
                    )
                )

            decoded = self.tokenizer.decode(
                result.sequences[0][inputs.shape[1]:],
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            )

            sentence = ""
            for char in decoded:
                sentence += char
                if char in ".!?":
                    yield sentence + " "
                    sentence = ""

            if sentence:
                yield sentence + " "

        except Exception as e:
            logger.error(f"Error in generation: {e}")
            yield f"Error: {e}"
