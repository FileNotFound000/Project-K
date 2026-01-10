import pyautogui
import base64
import io
import json
import os
from PIL import Image, ImageDraw
import google.generativeai as genai
from app.services.settings import SettingsService

class VisionService:
    def __init__(self):
        self.settings_service = SettingsService()
        self._configure_genai()

    def _configure_genai(self):
        settings = self.settings_service.load_settings()
        
        # Try to get from settings first, then env vars
        api_key = settings.get("providers", {}).get("gemini", {}).get("api_key")
        if not api_key:
            api_key = settings.get("api_key") # Legacy fallback
            
        if not api_key:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("GEMINI_API_KEY")

        if api_key:
            genai.configure(api_key=api_key)
            # Use Flash for speed and vision capabilities
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        else:
            print("Gemini API key not configured in settings or environment.")
            self.model = None

    def capture_screen(self):
        """
        Captures the screen and returns a PIL Image.
        """
        try:
            return pyautogui.screenshot()
        except Exception as e:
            print(f"Error capturing screen: {e}")
            return None

    def get_click_coordinates(self, description: str):
        """
        Analyzes the screen and finds the coordinates of the element matching the description.
        Returns (x, y) or None.
        """
        if not self.model:
            self._configure_genai()
            if not self.model:
                print("Gemini API key not configured.")
                return None

        screenshot = self.capture_screen()
        if not screenshot:
            return None
            
        screen_width, screen_height = screenshot.size

        # Create a clearer prompt for coordinate extraction
        # We don't necessarily need a grid if the model is good at spatial reasoning,
        # but asking for relative 0-1000 coordinates is often reliable for Gemini 1.5 Pro/Flash.
        prompt = f"""
        I am looking at a screenshot of a computer desktop. verify the resolution is {screen_width}x{screen_height}.
        Find the UI element described as: "{description}".
        
        Return the center coordinates of this element.
        Output MUST be a JSON object with keys "x" and "y".
        Example: {{"x": 500, "y": 300}}
        
        If the element is not visible, return null.
        """

        try:
            # Pass the image directly
            response = self.model.generate_content([prompt, screenshot])
            text = response.text
            
            # Extract JSON
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = text[start:end]
                coords = json.loads(json_str)
                return (int(coords['x']), int(coords['y']))
            else:
                print(f"Could not parse coordinates from: {text}")
                return None
                
        except Exception as e:
            print(f"Error analyzing screen: {e}")
            return None
