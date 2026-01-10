import google.generativeai as genai
import os
from typing import AsyncGenerator, List, Dict, Any
from app.services.llm_provider import LLMProvider
import PIL.Image
import io

class GeminiProvider(LLMProvider):
    def __init__(self):
        self.model = None
        self.api_key = None

    async def configure(self, settings: Dict[str, Any]):
        self.api_key = settings.get("api_key")
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY")
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            
            system_instruction = settings.get("system_instruction")
            if not system_instruction:
                system_instruction = None

            model_name = settings.get("model", "gemini-2.5-flash")
            
            self.model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
        else:
            print("Warning: No API key found for GeminiProvider")

    async def send_message_stream(
        self, 
        history: List[Dict[str, str]], 
        message: str, 
        images: List[bytes] = None
    ) -> AsyncGenerator[str, None]:
        
        if not self.model:
            yield "Error: Gemini model not configured."
            return

        # Convert generic history to Gemini format
        # Generic: [{"role": "user"|"model", "content": "..."}]
        # Gemini: [{"role": "user"|"model", "parts": ["..."]}]
        gemini_history = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        # Start a chat session with this history
        chat = self.model.start_chat(history=gemini_history)

        # Prepare content
        content = [message]
        if images:
            for img_bytes in images:
                try:
                    image = PIL.Image.open(io.BytesIO(img_bytes))
                    content.append(image)
                except Exception as e:
                    print(f"Error processing image: {e}")

        # Send message
        def log_debug(msg):
            with open("debug_gemini.log", "a") as f:
                f.write(f"{msg}\n")

        try:
            log_debug(f"DEBUG: GeminiProvider sending message: {content[:50]}...")
            response_stream = await chat.send_message_async(content, stream=True)
            log_debug("DEBUG: GeminiProvider got response stream")
            async for chunk in response_stream:
                log_debug(f"DEBUG: GeminiProvider chunk: {chunk}")
                
                # Log finish reason
                if chunk.candidates:
                    log_debug(f"DEBUG: Finish reason: {chunk.candidates[0].finish_reason}")
                    if chunk.candidates[0].safety_ratings:
                         log_debug(f"DEBUG: Safety ratings: {chunk.candidates[0].safety_ratings}")

                # Safely check if chunk has text
                if chunk.candidates and chunk.candidates[0].content.parts:
                    try:
                        text_content = chunk.text
                        if text_content:
                            log_debug(f"DEBUG: GeminiProvider yielding text: {text_content[:20]}...")
                            yield text_content
                    except ValueError:
                        log_debug("DEBUG: GeminiProvider ValueError accessing .text")
                        pass
                else:
                    log_debug("DEBUG: GeminiProvider chunk has no text parts")
        except Exception as e:
            log_debug(f"DEBUG: GeminiProvider Error: {e}")
            yield f"Error generating response: {str(e)}"

    async def get_embedding(self, text: str) -> List[float]:
        if not self.api_key:
            print("GeminiProvider: No API key for embedding.")
            return []
        try:
            # print(f"GeminiProvider: Generating embedding for '{text}' using models/text-embedding-004")
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document",
                title="Embedding of single string"
            )
            # print(f"GeminiProvider: Result keys: {result.keys()}")
            if 'embedding' in result:
                return result['embedding']
            else:
                print(f"GeminiProvider: 'embedding' not in result: {result}")
                return []
        except Exception as e:
            print(f"Error generating embedding with Gemini: {e}")
            return []
