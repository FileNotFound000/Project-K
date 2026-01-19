import os
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv
from app.core.db import add_message, get_session_messages
from app.services.llm_provider import LLMProvider
from app.providers.gemini import GeminiProvider
from app.providers.ollama import OllamaProvider

# System instruction for tool use
SYSTEM_INSTRUCTION = """
You are a helpful AI assistant with access to a computer.

TOOLS:
- remember: Save a fact to long-term memory. Use this when the user says "remember that..." or "my favorite X is Y". 
  Format: {"tool": "remember", "args": {"text": "fact to remember"}}
- execute_python: Execute Python code.
  Format: {"tool": "execute_python", "args": {"code": "print('hello')"}}
- google_search: Search the web.
  Format: {"tool": "google_search", "args": {"query": "weather in Tokyo"}}
- read_url: Read content from a URL.
  Format: {"tool": "read_url", "args": {"url": "https://example.com"}}
- system_control: Control the system.
  Format: {"tool": "system_control", "args": {"action": "open_app", "app_name": "calculator"}}
  Format: {"tool": "system_control", "args": {"action": "open_app", "app_name": "code ."}} (Open VS Code in current folder)
  Format: {"tool": "system_control", "args": {"action": "set_volume", "level": 50}}
  Format: {"tool": "system_control", "args": {"action": "mute"}}
  Format: {"tool": "system_control", "args": {"action": "unmute"}}
  Format: {"tool": "system_control", "args": {"action": "write_file", "path": "hello.py", "content": "print('Hello')"}}
  Format: {"tool": "system_control", "args": {"action": "read_file", "path": "hello.py"}}
  Format: {"tool": "system_control", "args": {"action": "list_files", "path": "."}}
  Format: {"tool": "system_control", "args": {"action": "replace_text", "path": "hello.py", "search_text": "Hello", "replace_text": "World"}}
  Format: {"tool": "system_control", "args": {"action": "screenshot"}}
  Format: {"tool": "system_control", "args": {"action": "media", "action_type": "play_pause"}}  (Options: play_pause, next, prev, stop)
  Format: {"tool": "system_control", "args": {"action": "power", "action_type": "sleep"}}  (Options: shutdown, restart, sleep, lock)
  Format: {"tool": "system_control", "args": {"action": "brightness", "level": 100}}
  Format: {"tool": "system_control", "args": {"action": "window", "action_type": "minimize"}}
  Format: {"tool": "system_control", "args": {"action": "interact", "action_type": "type", "text": "Hello"}}
  Format: {"tool": "system_control", "args": {"action": "interact", "action_type": "type", "text": "Hello"}}
  Format: {"tool": "system_control", "args": {"action": "interact", "action_type": "press", "key": "enter"}}
- click_on_ui: Click a UI element by description.
  Format: {"tool": "click_on_ui", "args": {"description": "the blue submit button"}}

CRITICAL RULES:
1. To use a tool, you MUST output the JSON command.
2. Do NOT output the result of the tool (e.g. {"result": true}). The system will execute it and give you the result.
3. You can include conversational text before or after the JSON, but the JSON must be valid.
4. Example: "I'll save that." {"tool": "remember", "args": {"text": "User likes blue"}}
5. Do NOT use the "remember" tool unless the user explicitly asks you to remember something or save a fact. Do NOT use it when answering questions based on existing memory.
6. CRITICAL: Output the JSON command at the END of your response. Do NOT output anything after the JSON. Do NOT simulate the tool output.
7. INTERACTION RULE: If the user asks you to "perform" something IN an app (e.g. "Calculate in Calculator", "Write in Notepad"), you must OPEN the app and then USE `interact` to type/press keys. Do NOT just calculate it yourself.
   - Correct: Open Calculator -> interact(type="128*4") -> interact(press="enter")
   - Correct: Open Calculator -> interact(type="128*4") -> interact(press="enter")
   - Incorrect: Open Calculator -> "The answer is 512."
8. WRITING RULE: If asked to write an essay or long text via `system_control` (type), generate the FULL text. Typing is instant. Do not summarize or output "Simulating writing...". Output the actual text in the `text` argument.
"""

class AgentService:
    def __init__(self):
        self.last_error = None
        self.code_interpreter = None
        self.memory_service = None
        self.provider: LLMProvider = None
        
        try:
            from app.services.code_interpreter import CodeInterpreterService
            self.code_interpreter = CodeInterpreterService()
        except Exception as e:
            print(f"Failed to init code interpreter: {e}")

        try:
            from app.services.memory import MemoryService
            self.memory_service = MemoryService()
        except Exception as e:
            print(f"Failed to init memory service: {e}")

        try:
            from app.services.system_control import SystemControlService
            self.system_control = SystemControlService()
        except Exception as e:
            print(f"Failed to init system control service: {e}")
            
        except Exception as e:
            print(f"Failed to init system control service: {e}")

        try:
            from app.services.vision_service import VisionService
            self.vision_service = VisionService()
        except Exception as e:
            print(f"Failed to init vision service: {e}")
            self.vision_service = None
            
        self._configure()

    def _configure(self, session_id: str = None):
        load_dotenv(override=True)
        
        # Load settings
        settings = {}
        try:
            from app.services.settings import SettingsService
            settings_service = SettingsService()
            settings = settings_service.load_settings()
        except Exception as e:
            print(f"Error loading settings: {e}")

        # Determine provider
        provider_name = settings.get("active_provider", "gemini")
        
        # Determine system prompt from active persona
        active_persona_id = settings.get("active_persona_id", "default")
        personas = settings.get("personas", [])
        
        # Find the active persona
        active_persona = next((p for p in personas if p["id"] == active_persona_id), None)
        
        # Fallback to default if not found
        if not active_persona:
             active_persona = {
                "system_prompt": "You are a helpful AI assistant. You can answer questions and also control the user's computer system."
             }
             
        # Combine base system instruction (tools) with persona prompt
        # We append the tool instructions to the persona prompt
        full_system_prompt = f"{active_persona['system_prompt']}\n\n{SYSTEM_INSTRUCTION}"
        
        # Update settings with the full system prompt so providers can use it
        settings["system_instruction"] = full_system_prompt

        # Factory logic
        if provider_name == "gemini":
            self.provider = GeminiProvider()
        elif provider_name == "ollama":
            self.provider = OllamaProvider()
            # Add specific instructions for local models to improve stability
            local_stability_prompt = """
            
            LOCAL MODEL INSTRUCTIONS:
            1. Be concise. Do not ramble.
            2. Do not repeat greetings or confirmations.
            3. When using tools, output ONLY the JSON.
            4. If a tool was just executed, acknowledge the result briefly and move on.
            5. Do NOT use 'execute_python' for simple printing or chatting. Only use it for calculations or data processing.
            6. Do NOT output empty JSONs like {"tool": ""}.
            7. To speak to the user, just output text. Do NOT use a tool like "say" or "speak".
            """
            settings["system_instruction"] += local_stability_prompt
        else:
            # Fallback to Gemini for now if unknown
            print(f"Unknown provider {provider_name}, falling back to Gemini")
            self.provider = GeminiProvider()
            
        # Configure provider
        # We schedule the async configuration
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.provider.configure(settings))
            else:
                loop.run_until_complete(self.provider.configure(settings))
        except RuntimeError:
            # No loop running (e.g. during simple script execution), try to run sync if possible or just ignore
            # For FastAPI, loop is usually running.
            pass
        except Exception as e:
            print(f"Error configuring provider: {e}")


        # Configure provider
        # Pass system instruction in settings for the provider to use if it supports it
        provider_settings = settings.copy()
        provider_settings["system_instruction"] = SYSTEM_INSTRUCTION
        
        pass

    async def generate_response(self, message: str, session_id: str, image_data: bytes = None, mime_type: str = None, context: str = None, save_user_message: bool = True) -> dict:
        """
        Returns a dict with 'text' and optional 'command'.
        """
        full_text = ""
        command = None
        async for chunk in self.generate_response_stream(message, session_id, image_data, mime_type, context, save_user_message):
            if "text" in chunk:
                full_text += chunk["text"]
            if "command" in chunk:
                command = chunk["command"]
        
        return {"text": full_text, "command": command}

    async def generate_response_stream(self, message: str, session_id: str, image_data: bytes = None, mime_type: str = None, context: str = None, save_user_message: bool = True):
        """
        Yields chunks of text. Handles ReAct loop for tools.
        """
        # Re-configure to ensure fresh settings/provider
        self._configure(session_id)
        
        # Configure provider (async)
        settings = {}
        try:
            from app.services.settings import SettingsService
            settings = SettingsService().load_settings()
        except: 
            pass
        settings["system_instruction"] = SYSTEM_INSTRUCTION
        await self.provider.configure(settings)

        try:
            # Save user message to DB
            if save_user_message:
                add_message(session_id, "user", message)
            
            # Retrieve memories
            memories = []
            if self.memory_service:
                try:
                    memories = await self.memory_service.search_memory(message, self.provider)
                except Exception as e:
                    print(f"Error searching memory: {e}")

            # Prepare initial message
            msg_content = message
            
            # Inject context and memories
            context_parts = []
            
            # User Profile Context
            user_profile = settings.get("user_profile", {})
            if user_profile.get("name") or user_profile.get("about_me"):
                profile_text = f"User Profile:\nName: {user_profile.get('name', 'User')}\nAbout Me: {user_profile.get('about_me', '')}"
                context_parts.append(profile_text)

            if context:
                context_parts.append(f"Context from uploaded documents:\n{context}")
            if memories:
                memory_text = "\n".join([f"- {m}" for m in memories])
                context_parts.append(f"Memory Context:\n{memory_text}")
                
            if context_parts:
                # Use a clear separator to distinguish context from user message
                context_block = "\n\n".join(context_parts)
                msg_content = f"System Context:\n{context_block}\n\nUser Message:\n{message}"

            # images = [image_data] if image_data else None
            images = None # DEBUG: Disable images to test if they are causing the error

            # ReAct Loop (Max 5 turns)
            accumulated_response = ""
            
            def log_debug(msg):
                with open("debug_agent.log", "a") as f:
                    f.write(f"{msg}\n")

            # RETRY LOGIC
            max_retries = 2
            for attempt in range(max_retries):
                has_yielded_content = False
                
                # Load history once per attempt
                history = []
                if session_id:
                    history = get_session_messages(session_id)

                # If this is a retry (attempt > 0), strip context to avoid safety filters
                current_msg_content = msg_content
                if attempt > 0:
                    log_debug(f"DEBUG: Retry attempt {attempt}. Stripping context.")
                    current_msg_content = message # Reset to just the user message
                    if memories: 
                         memory_text = "\n".join([f"- {m}" for m in memories])
                         current_msg_content = f"Memory Context:\n{memory_text}\n\nUser Message:\n{message}"

                # We maintain a local history for this generation session
                session_history = history.copy()
                executed_tools = set()

                for turn in range(5):
                    # Send to provider
                    log_debug(f"Turn {turn}: Sending message to provider...")
                    response_stream = self.provider.send_message_stream(session_history, current_msg_content, images)
                    
                    current_turn_text = ""
                    
                    async for text_chunk in response_stream:
                        log_debug(f"DEBUG: Received chunk: {text_chunk!r}")
                        current_turn_text += text_chunk
                        
                        # We yield text as it comes
                        yield {"text": text_chunk}
                        accumulated_response += text_chunk
                        has_yielded_content = True

                    # End of stream. Check for tool.
                    # End of stream. Check for tool.
                    import json
                    command = None
                    
                    # Robust JSON extraction
                    try:
                        # Find the first '{' that might start a tool JSON
                        # We scan for "tool" to check validity
                        start_indices = [i for i, char in enumerate(current_turn_text) if char == '{']
                        
                        for start in start_indices:
                            # Simple optimization: check if "tool" is somewhat near
                            # snippet = current_turn_text[start:start+100]
                            # if '"tool"' not in snippet and "'tool'" not in snippet: continue

                            # Stack-based brace counting
                            balance = 0
                            found_end = False
                            for i in range(start, len(current_turn_text)):
                                char = current_turn_text[i]
                                if char == '{':
                                    balance += 1
                                elif char == '}':
                                    balance -= 1
                                    if balance == 0:
                                        # Potential end of JSON
                                        candidate = current_turn_text[start:i+1]
                                        try:
                                            parsed = json.loads(candidate)
                                            if "tool" in parsed:
                                                command = parsed
                                                found_end = True
                                                
                                                # Correct the log logic to capture just this block
                                                # Re-assign json_match logic for history appending later
                                                class MockMatch:
                                                    def end(self): return i+1
                                                json_match = MockMatch()
                                                break
                                        except json.JSONDecodeError:
                                            # Keep trying, maybe we found an inner brace set
                                            pass
                            if found_end:
                                break
                                
                        if command:
                            log_debug(f"DEBUG: Extracted tool command: {command}")
                        else:
                            # Fallback to regex if brace counting fails (e.g. malformed)
                            # but usually brace counting is superior.
                            pass

                    except Exception as e:
                        log_debug(f"Failed to extract JSON: {e}")
                        command = None

                    if command and "tool" in command:
                        if not command["tool"]:
                            log_debug("DEBUG: Ignoring empty tool name.")
                            command = None
                        else:
                            # Check for duplicate execution
                            tool_signature = f"{command['tool']}:{json.dumps(command['args'], sort_keys=True)}"
                            if tool_signature in executed_tools:
                                log_debug(f"DEBUG: Skipping duplicate tool execution: {tool_signature}")
                                # Do not yield anything to user.
                                # Feed back to model to stop it.
                                current_msg_content = "Tool already executed. Do not repeat. Provide final answer."
                                images = None
                                continue
                            
                            executed_tools.add(tool_signature)

                            # Append the assistant's tool call to history so it knows what it did
                            # We truncate content after the JSON to prevent the model from learning to hallucinate tool outputs
                            if json_match:
                                end_index = json_match.end()
                                clean_content = current_turn_text[:end_index]
                                session_history.append({"role": "model", "content": clean_content})
                            else:
                                session_history.append({"role": "model", "content": current_turn_text})
                            
                            # Also append the user message that triggered this (if it was the first turn)
                            if turn == 0:
                                 session_history.append({"role": "user", "content": current_msg_content})

                            tool_name = command["tool"]
                            log_debug(f"DEBUG: Executing tool: {tool_name}")
                            
                            # Safely get args
                            tool_args = command.get("args", {})
                        
                            output_str = ""
                            if tool_name == "execute_python":
                                code = tool_args.get("code")
                                yield {"text": f"\n\n*Executing Code...*\n```python\n{code}\n```\n\n"}
                                accumulated_response += f"\n\n*Executing Code...*\n```python\n{code}\n```\n\n"
                                
                                if self.code_interpreter:
                                    result = self.code_interpreter.execute_code(code)
                                    output_str = f"Output:\n{result.get('output', '')}\nResult: {result.get('result', '')}"
                                    if result.get("error"):
                                        output_str += f"\nError: {result.get('error')}"
                                else:
                                    output_str = "Error: Code Interpreter not available."
                                    
                                yield {"text": f"*Result:*\n```\n{output_str}\n```\n\n"}
                                accumulated_response += f"*Result:*\n```\n{output_str}\n```\n\n"
                            
                            elif tool_name == "remember":
                                text_to_remember = tool_args.get("text")
                                
                                # Check if this fact is already in the retrieved memories to prevent hallucinations
                                # We do a fuzzy check or exact check against the 'memories' list we retrieved earlier
                                is_duplicate_intent = False
                                if memories:
                                    for mem in memories:
                                        # Simple check: if the new text is contained in an existing memory or vice versa
                                        # This handles "Color is blue" vs "My favorite color is blue"
                                        if text_to_remember and (text_to_remember.lower() in mem.lower() or mem.lower() in text_to_remember.lower()):
                                            is_duplicate_intent = True
                                            break
                                
                                if is_duplicate_intent:
                                    log_debug(f"DEBUG: Skipping duplicate memory save (hallucination prevention): {text_to_remember}")
                                    output_str = "Memory already exists. Do not re-save."
                                    # Do not yield UI message
                                else:
                                    yield {"text": f"\n\n*Saving to memory...*\n> {text_to_remember}\n\n"}
                                    accumulated_response += f"\n\n*Saving to memory...*\n> {text_to_remember}\n\n"
                                    
                                    if self.memory_service:
                                        success = await self.memory_service.add_memory(text_to_remember, self.provider)
                                        if success:
                                            output_str = "Memory saved successfully."
                                        else:
                                            output_str = "Error: Failed to save memory."
                                            yield {"text": f"\n\n*Failed to save memory.*\n\n"}
                                            accumulated_response += f"\n\n*Failed to save memory.*\n\n"
                                    else:
                                        output_str = "Error: Memory Service not available."

                            elif tool_name == "system_control":
                                action = tool_args.get("action")
                                
                                if self.system_control:
                                    if action == "open_app":
                                        app_name = tool_args.get("app_name")
                                        yield {"text": f"\n\n*Opening {app_name}...*\n\n"}
                                        accumulated_response += f"\n\n*Opening {app_name}...*\n\n"
                                        output_str = self.system_control.open_application(app_name)
                                    
                                    elif action == "set_volume":
                                        level = tool_args.get("level")
                                        yield {"text": f"\n\n*Setting volume to {level}%...*\n\n"}
                                        accumulated_response += f"\n\n*Setting volume to {level}%...*\n\n"
                                        output_str = self.system_control.set_volume(int(level))
                                    
                                    elif action == "mute":
                                        yield {"text": f"\n\n*Muting volume...*\n\n"}
                                        accumulated_response += f"\n\n*Muting volume...*\n\n"
                                        output_str = self.system_control.set_mute(True)

                                    elif action == "unmute":
                                        yield {"text": f"\n\n*Unmuting volume...*\n\n"}
                                        accumulated_response += f"\n\n*Unmuting volume...*\n\n"
                                        self.system_control.set_mute(False)
                                        output_str = "Success: Volume has been unmuted."

                                    elif action == "write_file":
                                        path = tool_args.get("path")
                                        content = tool_args.get("content")
                                        yield {"text": f"\n\n*Writing file {path}...*\n\n"}
                                        accumulated_response += f"\n\n*Writing file {path}...*\n\n"
                                        output_str = self.system_control.write_file(path, content)

                                    elif action == "read_file":
                                        path = tool_args.get("path")
                                        yield {"text": f"\n\n*Reading file {path}...*\n\n"}
                                        accumulated_response += f"\n\n*Reading file {path}...*\n\n"
                                        output_str = self.system_control.read_file(path)
                                    
                                    elif action == "list_files":
                                        path = tool_args.get("path", ".")
                                        yield {"text": f"\n\n*Listing files in {path}...*\n\n"}
                                        accumulated_response += f"\n\n*Listing files in {path}...*\n\n"
                                        output_str = self.system_control.list_files(path)

                                    elif action == "replace_text":
                                        path = tool_args.get("path")
                                        search_text = tool_args.get("search_text")
                                        replace_text = tool_args.get("replace_text")
                                        yield {"text": f"\n\n*Patching file {path}...*\n\n"}
                                        accumulated_response += f"\n\n*Patching file {path}...*\n\n"
                                        output_str = self.system_control.replace_text(path, search_text, replace_text)
                                    
                                    elif action == "screenshot":
                                        yield {"text": f"\n\n*Taking screenshot...*\n\n"}
                                        accumulated_response += f"\n\n*Taking screenshot...*\n\n"
                                        screenshot = self.system_control.take_screenshot()
                                        if screenshot:
                                            output_str = "Screenshot taken successfully."
                                        else:
                                            output_str = "Failed to take screenshot."

                                    elif action == "media":
                                        sub_action = tool_args.get("action_type") # e.g. "play_pause"
                                        yield {"text": f"\n\n*Media Control: {sub_action}*\n\n"}
                                        accumulated_response += f"\n\n*Media Control: {sub_action}*\n\n"
                                        output_str = self.system_control.media_control(sub_action)

                                    elif action == "power":
                                        sub_action = tool_args.get("action_type")
                                        yield {"text": f"\n\n*System Power: {sub_action}*\n\n"}
                                        accumulated_response += f"\n\n*System Power: {sub_action}*\n\n"
                                        output_str = self.system_control.system_power(sub_action)

                                    elif action == "brightness":
                                        level = tool_args.get("level")
                                        yield {"text": f"\n\n*Setting brightness to {level}%...*\n\n"}
                                        accumulated_response += f"\n\n*Setting brightness to {level}%...*\n\n"
                                        output_str = self.system_control.set_brightness(int(level))

                                    elif action == "window":
                                        sub_action = tool_args.get("action_type")
                                        yield {"text": f"\n\n*Window Control: {sub_action}*\n\n"}
                                        accumulated_response += f"\n\n*Window Control: {sub_action}*\n\n"
                                        output_str = self.system_control.window_control(sub_action)

                                    elif action == "interact":
                                        sub_action = tool_args.get("action_type") # type, press, hotkey
                                        yield {"text": f"\n\n*Simulating: {sub_action}*\n\n"}
                                        accumulated_response += f"\n\n*Simulating: {sub_action}*\n\n"
                                        
                                        # Filter out keys that might conflict or aren't needed
                                        interact_kwargs = {k: v for k, v in tool_args.items() if k not in ["action", "action_type"]}
                                        output_str = self.system_control.interact(sub_action, **interact_kwargs)

                                    else:
                                        output_str = f"Error: Unknown system control action '{action}'"
                                else:
                                    output_str = "Error: System Control Service not available."

                            elif tool_name == "google_search":
                                query = tool_args.get("query")
                                yield {"text": f"\n\n*Searching Google for '{query}'...*\n\n"}
                                accumulated_response += f"\n\n*Searching Google for '{query}'...*\n\n"
                                
                                try:
                                    from app.services.search import search_web
                                    results = search_web(query)
                                    output_str = f"Search Results:\n{results}"
                                except Exception as e:
                                    output_str = f"Error performing search: {e}"

                            elif tool_name == "read_url":
                                url = tool_args.get("url")
                                yield {"text": f"\n\n*Reading URL {url}...*\n\n"}
                                accumulated_response += f"\n\n*Reading URL {url}...*\n\n"
                                
                                try:
                                    # Fallback: simple requests or browser read
                                    # For now, let's use a simple scrape or system_control read if available
                                    # But since search_web is simple, let's assume we might need a scraper service
                                    # Let's check imports in main.py, it uses app.services.search.search_web
                                    # Does main.py have a read_url? No.
                                    # Let's try requests
                                    import requests
                                    from bs4 import BeautifulSoup
                                    
                                    try:
                                        resp = requests.get(url, timeout=10)
                                        soup = BeautifulSoup(resp.content, 'html.parser')
                                        
                                        # Remove script and style elements
                                        for script in soup(["script", "style"]):
                                            script.extract()
                                            
                                        text = soup.get_text()
                                        
                                        # Break into lines and remove leading and trailing space on each
                                        lines = (line.strip() for line in text.splitlines())
                                        # Break multi-headlines into a line each
                                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                                        # Drop blank lines
                                        text = '\n'.join(chunk for chunk in chunks if chunk)
                                        
                                        output_str = f"URL Content ({url}):\n{text[:2000]}..." # Truncate
                                    except Exception as e:
                                        output_str = f"Error reading URL: {e}"
                                        
                                except ImportError:
                                    output_str = "Error: requests or beautifulsoup4 not installed."

                            elif tool_name == "click_on_ui":
                                description = tool_args.get("description")
                                yield {"text": f"\n\n*Looking for '{description}'...*\n\n"}
                                accumulated_response += f"\n\n*Looking for '{description}'...*\n\n"
                                
                                if self.vision_service:
                                    coords = self.vision_service.get_click_coordinates(description)
                                    if coords:
                                        x, y = coords
                                        yield {"text": f"\n\n*Clicking at ({x}, {y})...*\n\n"}
                                        accumulated_response += f"\n\n*Clicking at ({x}, {y})...*\n\n"
                                        
                                        if self.system_control:
                                            # Use the new click capability
                                            self.system_control.interact("click", x=x, y=y)
                                            output_str = f"Clicked description '{description}' at ({x}, {y})."
                                        else:
                                            output_str = "Error: Vision found coordinates, but System Control unavailable for clicking."
                                    else:
                                        output_str = f"Could not find UI element matching '{description}'."
                                else:
                                    output_str = "Error: Vision Service not available."

                            else:
                                # Unknown tool, just finish
                                yield {"command": command}
                                add_message(session_id, "model", accumulated_response)
                                return

                            # Prepare for next turn
                            # The new "message" is the tool result
                            current_msg_content = f"Tool Result: {output_str}\n(Action completed. Do not call this tool again. Provide final answer.)"
                            images = None # Don't send images again
                            continue

                    # No tool called, we are done
                    add_message(session_id, "model", accumulated_response)
                    return 

                # End of turns loop
                if has_yielded_content:
                    break 
                else:
                    # Retry logic...
                    if attempt < max_retries - 1:
                        yield {"text": "\n\n*Thinking... (Retrying without context)*\n\n"}
                        continue 
                    else:
                        yield {"text": "I'm sorry, I couldn't generate a response."}

        except Exception as e:
            print(f"Error generating response stream: {e}")
            yield {"text": f"I'm sorry, I encountered an error: {str(e)}"}

    def get_history(self) -> List[Dict[str, Any]]:
        return []
