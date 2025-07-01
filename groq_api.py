import os
import requests
from dotenv import load_dotenv

# Load environment variables
def load_api_key():
    load_dotenv()
    return os.getenv("GROQ_API_KEY")

def load_story_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "story_qa_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
story_prompt = load_story_prompt()

def get_llm_response(messages, system_prompt=None):
    """
    Get response from Groq LLM using the story prompt as system prompt if not provided.
    """
    try:
        api_key = load_api_key()
        sys_prompt = system_prompt if system_prompt else story_prompt
        full_messages = [{"role": "system", "content": sys_prompt}] + messages
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": full_messages,
            "temperature": 0.8,
            "max_tokens": 1024,
            "top_p": 0.9
        }
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"