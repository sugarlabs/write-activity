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
    """
    Get AI feedback on provided text using the configured backend.
    
    This provides a simple function-based interface to the LLM functionality
    without having to manage the LLMManager instance directly.
    
    Args:
        text: The text to analyze
        prompt_type: Optional prompt type (grammar, style, etc.)
        backend: Optional backend to use (local, openai), defaults to config setting
        
    Returns:
        An async generator yielding response tokens
    """
    manager = LLMManager()
    manager.initialize(backend_type=backend)
    return manager.get_feedback(text, prompt_type)

async def get_tokens_list(text, prompt_type=None, backend=None) -> List[str]:
    """
    Get AI feedback as a list of tokens (async version).
    
    Args:
        text: The text to analyze
        prompt_type: Optional prompt type (grammar, style, etc.)
        backend: Optional backend to use (local, openai), defaults to config setting
        
    Returns:
        A list of tokens from the model
    """
    manager = LLMManager()
    manager.initialize(backend_type=backend)
    return await manager.get_feedback_as_list(text, prompt_type)

def get_feedback_sync(text, prompt_type=None, backend=None) -> str:
    """
    Get AI feedback as a single string response (synchronous version).
    
    This function should only be used when you're not in an event loop.
    For code running inside an event loop or async function, use get_tokens_list instead.
    
    Args:
        text: The text to analyze
        prompt_type: Optional prompt type (grammar, style, etc.)
        backend: Optional backend to use (local, openai), defaults to config setting
        
    Returns:
        A string containing the complete model response
    """
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