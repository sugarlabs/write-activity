import sys
from pathlib import Path

# Add the parent directory to sys.path to allow importing from llm
sys.path.insert(0, str(Path(__file__).parent.parent))

# First ensure setup is complete
from . import setup
setup.init()

from .config import LLMConfig
from .llm_manager import LLMManager
import asyncio
from typing import List

# Export commonly used classes and functions
__all__ = ['LLMManager', 'LLMConfig', 'get_feedback', 'get_feedback_sync', 'get_tokens_list']

def get_feedback(text, prompt_type=None, backend=None):
    
    manager = LLMManager()
    manager.initialize(backend_type=backend)
    return manager.get_feedback(text, prompt_type)

async def get_tokens_list(text, prompt_type=None, backend=None) -> List[str]:
   
    manager = LLMManager()
    manager.initialize(backend_type=backend)
    return await manager.get_feedback_as_list(text, prompt_type)

def get_feedback_sync(text, prompt_type=None, backend=None) -> str:
   
    # Create a new event loop only if there isn't one already running
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in a running event loop, we shouldn't use run_until_complete
            raise RuntimeError("Cannot use get_feedback_sync in a running event loop. Use get_tokens_list instead.")
        tokens = loop.run_until_complete(get_tokens_list(text, prompt_type, backend))
    except RuntimeError:
        # Create a new event loop if one doesn't exist or we can't use the current one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            tokens = loop.run_until_complete(get_tokens_list(text, prompt_type, backend))
        finally:
            loop.close()
    
    # Return complete response as string
    return ''.join(tokens) 