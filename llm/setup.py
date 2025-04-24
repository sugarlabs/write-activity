import os
import sys
import venv
import subprocess
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from llm.config import LLMConfig

class EnvironmentSetup:
    _done = False

    @property
    def python(self): return LLMConfig.VENV_DIR / "bin" / "python"
    @property
    def pip(self): return LLMConfig.VENV_DIR / "bin" / "pip"

    def venv_is_valid(self):
        """Validate virtual environment and required packages"""
        if not self.python.exists() or not self.pip.exists():
            return False
        try:
            result = subprocess.run(
                [self.pip, "freeze"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            installed = {pkg.split('==')[0].lower() for pkg in result.stdout.split()}
            required = {'torch', 'transformers', 'openai', 'python-dotenv', 'groq'}
            return required.issubset(installed)
        except subprocess.SubprocessError:
            return False

    def create_venv(self):
        
        if LLMConfig.VENV_DIR.exists():
            shutil.rmtree(LLMConfig.VENV_DIR)
        print("Creating virtual environment...")
        venv.create(LLMConfig.VENV_DIR, with_pip=True)
        subprocess.run([self.python, "-m", "pip", "install", "--upgrade", "pip"], check=True)

    def install_deps(self):
        
        print("Installing dependencies...")
        try:
            subprocess.run([self.pip, "install", "-r", LLMConfig.REQUIREMENTS_FILE], check=True)
        except subprocess.SubprocessError as e:
            print(f"Error installing dependencies: {e}")
            return False
        return True

    def load_env(self):
        """Load environment variables from .env file"""
        try:
            from dotenv import load_dotenv
            dotenv_path = LLMConfig.BASE_DIR / '.env'
            if not dotenv_path.exists():
                print("Warning: .env file not found. Please create one with your API keys.")
                return False
            load_dotenv(dotenv_path)
            return True
        except ImportError:
            print("Warning: python-dotenv not installed. Environment variables must be set manually.")
            return False

    def setup(self):
        """Setup the environment """
        if EnvironmentSetup._done:
            return True

        try:
            if not LLMConfig.VENV_DIR.exists() or not self.venv_is_valid():
                self.create_venv()
                if not self.install_deps():
                    return False

            sys.path.append(str(LLMConfig.get_site_packages_path()))
            if not self.load_env():
                return False

            LLMConfig.MODEL_CACHE_DIR.mkdir(exist_ok=True)
            EnvironmentSetup._done = True
            return True

        except Exception as e:
            print(f"Environment setup failed: {e}")
            return False

def init():
    return EnvironmentSetup().setup()

if __name__ == "__main__":
    init()
