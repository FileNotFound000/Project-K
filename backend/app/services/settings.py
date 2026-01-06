import json
import os
from typing import Dict, Any

SETTINGS_FILE = "user_settings.json"

DEFAULT_SETTINGS = {
    "active_provider": "gemini",
    "providers": {
        "gemini": {
            "api_key": "",
            "model": "gemini-1.5-flash"
        },
        "openai": {
            "api_key": "",
            "model": "gpt-4o"
        },
        "ollama": {
            "base_url": "http://localhost:11434", 
            "model": "llama3"
        }
    },
    "active_persona_id": "default",
    "personas": [
        {
            "id": "default",
            "name": "K",
            "description": "Your helpful AI assistant.",
            "system_prompt": "You are a helpful AI assistant. You can answer questions and also control the user's computer system."
        },
        {
            "id": "coder",
            "name": "Strict Coder",
            "description": "Focused on clean, efficient code.",
            "system_prompt": "You are an expert software engineer. Provide concise, correct, and efficient code. Prioritize best practices and avoid unnecessary chatter."
        },
        {
            "id": "teacher",
            "name": "Teacher",
            "description": "Explains concepts simply and patiently.",
            "system_prompt": "You are a patient and knowledgeable teacher. Explain complex topics in simple terms, using analogies where appropriate. Encourage the user to ask questions."
        }
    ],
    "theme": "dark",
    "voice": "default",
    "user_profile": {
        "name": "User",
        "about_me": ""
    },
    # Legacy support
    "api_key": "" 
}

class SettingsService:
    def __init__(self):
        self.settings_file = SETTINGS_FILE
        self._ensure_settings_file()

    def _ensure_settings_file(self):
        if not os.path.exists(self.settings_file):
            self.save_settings(DEFAULT_SETTINGS)

    def load_settings(self) -> Dict[str, Any]:
        try:
            with open(self.settings_file, "r") as f:
                user_settings = json.load(f)
                # Merge with defaults to ensure new keys exist
                # Deep merge would be better but for now shallow merge of top keys is enough
                # since we introduced new top level keys.
                final_settings = DEFAULT_SETTINGS.copy()
                final_settings.update(user_settings)
                
                # Ensure nested 'providers' dict is also merged if it exists in user_settings
                # (In case user has partial providers config)
                if "providers" in user_settings:
                     # If user has providers, we might want to ensure all default providers exist
                     # But for now, let's just trust the top level merge for the missing 'providers' key case.
                     pass
                     
                return final_settings
        except (FileNotFoundError, json.JSONDecodeError):
            return DEFAULT_SETTINGS

    def save_settings(self, settings: Dict[str, Any]):
        # Merge with existing to prevent overwriting missing keys with nothing
        current = self.load_settings()
        current.update(settings)
        
        with open(self.settings_file, "w") as f:
            json.dump(current, f, indent=4)
        return current
