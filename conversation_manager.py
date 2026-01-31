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

import json
import os
from sugarai_api import get_llm_response, get_llm_response_framework

# Extract story info from conversation using LLM analysis prompt
def extract_story_info(messages):
    analysis_prompt = (
        "Analyze this conversation and extract key story elements.\n"
        "Return ONLY a valid JSON object with these exact fields (leave empty string if not mentioned):\n"
        "{\n"
        "    \"title\": \"\",\n"
        "    \"setting\": \"\",\n"
        "    \"main_character\": \"\",\n"
        "    \"side_character\": \"\",\n"
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
    analysis = get_llm_response_framework(messages, analysis_prompt)
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
        "main_character": "",
        "side_character": "",
        "goal": "",
        "conflict": "",
        "climax": "",
        "helpers": "",
        "villains": "",
        "ending": "",
        "theme": ""
    }

# In-memory conversation context
class ConversationContext:
    def __init__(self):
        self.messages = [
            {"role": "assistant", "content": "Hi there!👋I am Mary Tales. Who is this story about?✨"}
        ]
        self.story_info = {
            "title": "",
            "setting": "",
            "main_character": "",
            "side_character": "",
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
  