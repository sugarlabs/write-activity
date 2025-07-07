import json
import os
from groq_api import get_llm_response

# Extract story info from conversation using LLM analysis prompt
def extract_story_info(messages):
    analysis_prompt = (
        "Analyze this conversation and extract key story elements.\n"
        "Return ONLY a valid JSON object with these exact fields (leave empty string if not mentioned):\n"
        "{\n"
        "    \"title\": \"\",\n"
        "    \"setting\": \"\",\n"
        "    \"character_main\": \"\",\n"
        "    \"character_side\": \"\",\n"
        "    \"goal\": \"\",\n"
        "    \"conflict\": \"\",\n"
        "    \"climax\": \"\",\n"
        "    \"helpers\": \"\",\n"
        "    \"villains\": \"\",\n"
        "    \"ending\": \"\",\n"
        "    \"theme\": \"\"\n"
        "}\n"
        "Do not include any other text or explanation, just the JSON object."
    )
    analysis = get_llm_response(messages, analysis_prompt)
    try:
        start_idx = analysis.find('{')
        end_idx = analysis.rfind('}') + 1
        if start_idx != -1 and end_idx != -1:
            json_str = analysis[start_idx:end_idx]
            story_data = json.loads(json_str)
            return story_data
    except Exception:
        pass
    # Return default structure if parsing fails
    return {
        "title": "",
        "setting": "",
        "character_main": "",
        "character_side": "",
        "goal": "",
        "conflict": "",
        "climax": "",
        "helpers": "",
        "villains": "",
        "ending": "",
        "theme": ""
    }

# Write framework JSON to file
def write_framework_json(story_info, file_name):
    try:
        # Get the directory of the current script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the full path to the target directory: output/
        target_dir = os.path.join(base_dir, "output")
        # Make sure the directory exists
        os.makedirs(target_dir, exist_ok=True)
        # Full path to the JSON file
        file_path = os.path.join(target_dir, file_name)

        # Write the JSON data
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(story_info, f, indent=2, ensure_ascii=False)

        print(f"Successfully wrote framework to {file_path}")
    except Exception as e:
        print(f"Error writing framework file: {str(e)}")
        print(f"Error writing framework file: {str(e)}")

# In-memory conversation context
class ConversationContext:
    def __init__(self):
        self.messages = [
            {"role": "assistant", "content": "Hi there!👋I am Mary Tales. Who is this story about?✨"}
        ]
        self.story_info = {
            "title": "",
            "setting": "",
            "character_main": "",
            "character_side": "",
            "goal": "",
            "conflict": "",
            "climax": "",
            "helpers": "",
            "villains": "",
            "ending": "",
            "theme": ""
        }

    def add_user_message(self, content):
        self.messages.append({"role": "user", "content": content})

    def add_bot_message(self, content):
        self.messages.append({"role": "assistant", "content": content})

    def get_latest_context(self):
        return self.messages

    def get_llm_response(self, messages, system_prompt=None):
        return get_llm_response(messages, system_prompt)

    def update_story_info(self):
        self.story_info = extract_story_info(self.messages)

    def write_framework(self, file_path="outputs/story_framework.json"):
        self.update_story_info()
        write_framework_json(self.story_info, file_path)