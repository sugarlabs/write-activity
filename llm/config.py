from pathlib import Path
import sys
import os
from typing import Optional


ENV_FILE_NAME = ".env"
SUPPORTED_BACKENDS = {"qwen", "openai", "llama"}
backend_ai = "qwen"

def load_environment():
    """Load environment variables from .env file if it exists"""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent / ENV_FILE_NAME
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)
    except ImportError:
        pass  


load_environment()

# === Configuration ===
class LLMConfig:
    BASE_DIR = Path(__file__).parent
    VENV_DIR = BASE_DIR / "venv"
    MODEL_CACHE_DIR = BASE_DIR / "model_cache"
    REQUIREMENTS_FILE = BASE_DIR / "requirements.txt"

    # Core configuration
    BACKEND_TYPE = os.getenv("BACKEND_TYPE", backend_ai)
    MODEL_NAME = "Qwen/Qwen2-0.5B-Chat"
    SYSTEM_PROMPT = """You are a creative AI assistant that assist children in writing.
1. you give grammatical assistance
2. Do not provide unwanted responses
3. Keep the it concise and evocative
 
"""

    MODEL_PARAMS = {
        "max_new_tokens": 200,
        "temperature": 0.1,
        "top_p": 0.95,
    }

    @classmethod
    def get_dependencies(cls) -> list[str]:
        """Read required dependencies"""
        if not cls.REQUIREMENTS_FILE.exists():
            raise FileNotFoundError(f"Requirements file not found at {cls.REQUIREMENTS_FILE}")
        with open(cls.REQUIREMENTS_FILE) as f:
            return [line.strip() for line in f if line.strip()]

    @classmethod
    def get_site_packages_path(cls) -> Path:
        """Locate the appropriate site-packages directory"""
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        paths = [
            cls.VENV_DIR / "lib" / py_ver / "site-packages",
            cls.VENV_DIR / "lib64" / py_ver / "site-packages"
        ]
        return next((p for p in paths if p.exists()), paths[0])

    @classmethod
    def get_api_key(cls, backend_type: Optional[str] = None) -> Optional[str]:
        
        backend = backend_type or cls.BACKEND_TYPE
        if backend == "openai":
            return os.getenv("OPENAI_API_KEY")
        elif backend == "llama":
            return os.getenv("GROQ_API_KEY")
        return None

    @classmethod
    def validate_config(cls) -> bool:
        
        if cls.BACKEND_TYPE not in SUPPORTED_BACKENDS:
            raise ValueError(f"Invalid backend type: {cls.BACKEND_TYPE}. Supported: {SUPPORTED_BACKENDS}")

        # Skip key check for local qwen
        if cls.BACKEND_TYPE == "qwen":
            return True

        # Check API key for OpenAI and LLaMA backends
        api_key = cls.get_api_key()
        if not api_key:
            print(f"API key not found for backend '{cls.BACKEND_TYPE}'")
            return False

        return True
