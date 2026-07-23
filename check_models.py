# import google.generativeai as genai
# from google import genai
import google.genai as genai
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='backend/.env')

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    # Try loading from user_settings.json if .env fails
    import json
    try:
        with open('backend/user_settings.json', 'r') as f:
            settings = json.load(f)
            api_key = settings.get('providers', {}).get('gemini', {}).get('api_key')
            if not api_key:
                 api_key = settings.get('api_key')
    except:
        pass

if not api_key:
    print("Error: Could not find GEMINI_API_KEY in backend/.env or backend/user_settings.json")
    exit(1)

print(f"Using API Key: {api_key[:5]}...{api_key[-5:]}")

try:
    genai.configure(api_key=api_key)
    print("\nListing available Gemini models:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error accessing Gemini API: {e}")
