from fastapi import FastAPI, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
import json
import asyncio
from typing import List
from dotenv import load_dotenv
from app.services.agent import AgentService
from app.services.search import search_web
from app.services.tts import generate_audio
from app.core.db import init_db, create_session, get_sessions, get_session_messages, delete_session, update_session_title
from app.services.system_control import SystemControlService
from app.services.rag import ingest_document, retrieve_context
from app.services.research import generate_research_report
from app.services.voice_listener import VoiceListenerService
import shutil

load_dotenv()

import sys
with open("env_info.txt", "w") as f:
    f.write(f"Executable: {sys.executable}\n")
    f.write(f"Path: {sys.path}\n")

app = FastAPI(title="AI Assistant Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database
init_db()

# Mount static directory for audio files
if not os.path.exists("static/audio"):
    os.makedirs("static/audio")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Globals
voice_listener = None
main_event_loop = None
active_websockets: List[WebSocket] = []

async def broadcast_wake_word():
    """Send wake word event to all connected clients"""
    if not active_websockets:
        return
    
    print("Broadcasting WAKE WORD to clients...")
    to_remove = []
    for ws in active_websockets:
        try:
            await ws.send_json({"type": "WAKE_WORD_DETECTED", "text": "karan"})
        except Exception as e:
            print(f"Failed to send to websocket: {e}")
            to_remove.append(ws)
    
    for ws in to_remove:
        if ws in active_websockets:
            active_websockets.remove(ws)

def on_wake_word_detected():
    """Callback from VoiceListener (runs in thread)"""
    if main_event_loop:
        asyncio.run_coroutine_threadsafe(broadcast_wake_word(), main_event_loop)

@app.on_event("startup")
async def startup_event():
    global voice_listener, main_event_loop
    main_event_loop = asyncio.get_running_loop()
    
    print("Initializing Voice Listener...")
    try:
        voice_listener = VoiceListenerService(wake_word="karan")
        if voice_listener.initialize():
            voice_listener.on_wake_word(on_wake_word_detected)
            # voice_listener.start() # Wait for frontend to request start
        else:
            print("Voice Listener failed to initialize.")
    except Exception as e:
         print(f"Error starting Voice Listener: {e}")

# Initialize services
try:
    print("Initializing AgentService...")
    llm_service = AgentService()
    if llm_service and llm_service.code_interpreter:
        print("Code Interpreter initialized successfully.")
    else:
        print("Code Interpreter NOT initialized.")
except Exception as e:
    print(f"Failed to initialize Agent Service: {e}")
    llm_service = None

try:
    system_control_service = SystemControlService()
except Exception as e:
    print(f"Failed to initialize System Control Service: {e}")
    system_control_service = None
try:
    from app.services.settings import SettingsService
    settings_service = SettingsService()
except Exception as e:
    print(f"Failed to initialize Settings Service: {e}")
    settings_service = None

@app.post("/voice/start")
async def start_voice_listener():
    global voice_listener
    if voice_listener:
        if not voice_listener.is_running:
             voice_listener.start()
        return {"status": "started", "message": "Voice listener started"}
    raise HTTPException(status_code=500, detail="Voice Listener not initialized")

@app.post("/voice/stop")
async def stop_voice_listener():
    global voice_listener
    if voice_listener:
        if voice_listener.is_running:
            voice_listener.stop()
        return {"status": "stopped", "message": "Voice listener stopped"}
    raise HTTPException(status_code=500, detail="Voice Listener not initialized")

@app.websocket("/ws/voice_status")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in active_websockets:
            active_websockets.remove(websocket)

@app.get("/")
async def root():
    return {"message": "AI Assistant Backend is running"}

# Settings Endpoints
@app.get("/settings")
async def get_settings():
    if not settings_service:
        raise HTTPException(status_code=500, detail="Settings Service not available")
    return settings_service.load_settings()

@app.post("/settings")
async def update_settings(settings: dict):
    if not settings_service:
        raise HTTPException(status_code=500, detail="Settings Service not available")
    return settings_service.save_settings(settings)

# Memory Endpoints
@app.get("/memories")
async def get_memories():
    if not llm_service or not llm_service.memory_service:
        raise HTTPException(status_code=500, detail="Memory Service not available")
    return {"memories": llm_service.memory_service.get_all_memories()}

@app.delete("/memories")
async def clear_memories():
    if not llm_service or not llm_service.memory_service:
        raise HTTPException(status_code=500, detail="Memory Service not available")
    llm_service.memory_service.clear_memories()
    return {"message": "All memories cleared"}


# Session Endpoints
@app.post("/sessions")
async def create_new_session(title: str = Form("New Chat")):
    session_id = create_session(title)
    return {"id": session_id, "title": title}

@app.get("/sessions")
async def list_sessions():
    return get_sessions()

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    messages = get_session_messages(session_id)
    return {"messages": messages}

@app.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    delete_session(session_id)
    
    # Cleanup audio files for this session
    session_audio_dir = os.path.join("static", "audio", session_id)
    if os.path.exists(session_audio_dir) and session_id.strip(): # Check strip to avoid deleting root audio if empty
        try:
            shutil.rmtree(session_audio_dir)
            print(f"Deleted audio content for session: {session_id}")
        except Exception as e:
            print(f"Failed to delete audio contents: {e}")
            
    return {"message": "Session deleted"}

@app.put("/sessions/{session_id}")
async def update_chat_session(session_id: str, title: str = Form(...)):
    update_session_title(session_id, title)
    return {"id": session_id, "title": title}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        # Save file temporarily
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Ingest
        result = ingest_document(temp_path, file.filename)
        
        # Cleanup
        os.remove(temp_path)
        
        return {"message": result}
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/knowledge")
async def clear_knowledge_base_endpoint():
    from app.services.rag import clear_knowledge_base
    if clear_knowledge_base():
        return {"message": "Knowledge base cleared successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to clear knowledge base")

@app.post("/chat")
async def chat(message: str = Form(...), session_id: str = Form(...), file: UploadFile = File(None)):
    if not llm_service:
        raise HTTPException(status_code=500, detail="LLM Service not available")
    
    image_data = None
    mime_type = None
    if file:
        image_data = await file.read()
        mime_type = file.content_type

    async def event_generator():
        user_message = message
        
        # Simple intent detection for search
        if "search for" in user_message.lower() or "google" in user_message.lower():
            # Perform search synchronously for now
            search_query = user_message.replace("search for", "").replace("google", "").strip()
            search_results = search_web(search_query)
            prompt = f"User asked: {user_message}\n\nSearch Results:\n{search_results}\n\nProvide a helpful answer based on the search results."
            
            async for chunk in llm_service.generate_response_stream(prompt, session_id=session_id):
                if "text" in chunk:
                    payload = json.dumps({"text": chunk['text']})
                    yield f"data: {payload}\n\n"
                elif "command" in chunk:
                    cmd = chunk['command']
                    if system_control_service and "tool" in cmd:
                        tool_name = cmd["tool"]
                        args = cmd.get("args", {})
                        print(f"Executing tool: {tool_name} with args: {args}")
                        
                        execution_result = ""
                        if tool_name == "set_volume":
                            execution_result = system_control_service.set_volume(args.get("level", 50))
                        elif tool_name == "mute_volume":
                            execution_result = system_control_service.mute_volume()
                        elif tool_name == "open_application":
                            execution_result = system_control_service.open_application(args.get("app_name"))
                        
                        yield f"event: command\ndata: {json.dumps(cmd)}\n\n"
        elif user_message.lower().startswith("research "):
            # Research Mode
            topic = user_message[9:].strip()
            
            # Save the user's original message to DB manually, since we disabled it in the service
            from app.core.db import add_message
            add_message(session_id, "user", user_message)
            
            async for chunk in generate_research_report(topic, llm_service, session_id):
                if "text" in chunk:
                    payload = json.dumps({"text": chunk['text']})
                    yield f"data: {payload}\n\n"
        else:
            # Retrieve context from RAG
            context = retrieve_context(user_message)
            print(f"Retrieved context: {context[:100]}...") # Debug log

            async for chunk in llm_service.generate_response_stream(user_message, session_id=session_id, image_data=image_data, mime_type=mime_type, context=context):
                if "text" in chunk:
                    payload = json.dumps({"text": chunk['text']})
                    yield f"data: {payload}\n\n"
                elif "command" in chunk:
                    cmd = chunk['command']
                    if system_control_service and "tool" in cmd:
                        tool_name = cmd["tool"]
                        args = cmd.get("args", {})
                        print(f"Executing tool: {tool_name} with args: {args}")
                        
                        execution_result = ""
                        if tool_name == "set_volume":
                            execution_result = system_control_service.set_volume(args.get("level", 50))
                        elif tool_name == "mute_volume":
                            execution_result = system_control_service.mute_volume()
                        elif tool_name == "open_application":
                            execution_result = system_control_service.open_application(args.get("app_name"))
                        
                        yield f"event: command\ndata: {json.dumps(cmd)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/tts")
async def text_to_speech(text: str = Form(...), session_id: str = Form(None)):
    try:
        # Get voice from settings
        voice = "en-US-ChristopherNeural" # Default
        if settings_service:
            settings = settings_service.load_settings()
            user_voice = settings.get("voice", "default")
            
            # Map friendly names to Edge TTS voices
            voice_map = {
                "default": "en-US-ChristopherNeural",
                "alloy": "en-US-AvaNeural",
                "echo": "en-US-AndrewNeural",
                "fable": "en-US-EmmaNeural",
                "onyx": "en-US-ChristopherNeural",
                "nova": "en-US-BrianNeural",
                "shimmer": "en-US-AnaNeural"
            }
            voice = voice_map.get(user_voice, "en-US-ChristopherNeural")

        audio_file = await generate_audio(text, voice, session_id=session_id)
        return {"audio_url": f"/static/audio/{audio_file}"}
    except Exception as e:
        print(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
