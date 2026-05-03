from google import genai
from google.genai import types
import os
from typing import AsyncGenerator, List, Dict, Any
from app.services.llm_provider import LLMProvider
import PIL.Image
import io

class GeminiProvider(LLMProvider):
    def __init__(self):
        self.client = None
        self.model_name = "gemini-2.5-flash"
        self.system_instruction = None
        self.api_key = None

    async def configure(self, settings: Dict[str, Any]):
        self.api_key = settings.get("api_key")
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY")
        
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            self.system_instruction = settings.get("system_instruction")
            self.model_name = settings.get("model", "gemini-2.5-flash")
        else:
            print("Warning: No API key found for GeminiProvider")

    async def send_message_stream(
        self, 
        history: List[Dict[str, str]], 
        message: str, 
        images: List[bytes] = None
    ) -> AsyncGenerator[str, None]:
        
        if not self.client:
            yield "Error: Gemini model not configured."
            return

        gemini_history = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))

        parts = [types.Part.from_text(text=message)]
        if images:
            for img_bytes in images:
                try:
                    image = PIL.Image.open(io.BytesIO(img_bytes))
                    parts.append(types.Part.from_image(image=image))
                except Exception as e:
                    print(f"Error processing image: {e}")

        gemini_history.append(types.Content(role="user", parts=parts))

        def log_debug(msg):
            with open("debug_gemini.log", "a") as f:
                f.write(f"{msg}\n")

        try:
            log_debug("DEBUG: GeminiProvider sending message via genai SDK")
            
            config = types.GenerateContentConfig()
            if self.system_instruction:
                config.system_instruction = self.system_instruction
                
            response_stream = await self.client.aio.models.generate_content_stream(
                model=self.model_name,
                contents=gemini_history,
                config=config
            )
            
            log_debug("DEBUG: GeminiProvider got response stream")
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            log_debug(f"DEBUG: GeminiProvider Error: {e}")
            yield f"Error generating response: {str(e)}"

    async def get_embedding(self, text: str) -> List[float]:
        if not self.api_key or not self.client:
            print("GeminiProvider: No API key for embedding.")
            return []
        try:
            # google-genai specific synchronous embedding call
            result = self.client.models.embed_content(
                model="text-embedding-004",
                contents=text,
            )
            # embeddings is a list of EmbedContentResponse, we need .embeddings[0].values
            if result.embeddings:
                return result.embeddings[0].values
            return []
        except Exception as e:
            print(f"Error generating embedding with Gemini: {e}")
            return []
