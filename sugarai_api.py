# Copyright (C) 2006 by Martin Sevior
# Copyright (C) 2006-2007 Marc Maurer <uwog@uwog.net>
# Copyright (C) 2007, One Laptop Per Child
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)
api_key = os.getenv("SUGAR_AI_API_KEY")
sugar_ai_url = "https://ai.sugarlabs.org"
local_url = "http://localhost:8000"

def load_url():
    try:
        response = requests.head(sugar_ai_url, timeout=2)
        if response.ok:
            return sugar_ai_url
    except requests.RequestException:
        pass
    
    return local_url

def load_story_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "story_qa_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

SUGAR_AI_API_URL = load_url()
story_prompt = load_story_prompt()

def get_llm_response(messages, system_prompt=None):
    """
    Get response from LLM using the story prompt as system prompt if not provided.
    """
    try:
        sys_prompt = system_prompt if system_prompt else story_prompt
        full_messages = [{"role": "system", "content": sys_prompt}] + messages
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "chat": True,
            "messages": full_messages,
            "max_length": 512,
            "temperature": 0.6,
            "top_p": 0.9,
            "top_k": 50
        }

        response = requests.post(
            f"{SUGAR_AI_API_URL}/ask-llm-prompted",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"
    
def get_llm_response_framework(messages, custom_prompt):
    """
    Get response from LLM using the /ask-llm-prompted endpoint for structured responses.
    This endpoint is better for avoiding hallucination in structured tasks.

    Returns:
        str: The answer content from the LLM response
    """
    try:      
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        
        # Convert messages list to a single string for the question parameter
        question_text = "\n".join(f"{msg['role']}: {msg['content']}" for msg in messages)
        
        payload = {
            "question": question_text,
            "custom_prompt": custom_prompt,
            "max_length": 1024,
            "truncation": True,
            "repetition_penalty": 1.1,
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 50
        }
        
        response = requests.post(f"{SUGAR_AI_API_URL}/ask-llm-prompted", headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        return data["answer"]
        
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"
