import os
import json
import pyaudio
import asyncio
from vosk import Model, KaldiRecognizer
from typing import Callable, Optional

class VoiceListenerService:
    def __init__(self, model_path: str = "model", wake_word: str = "karan"):
        self.model_path = model_path
        self.wake_word = wake_word.lower()
        self.is_running = False
        self.callback: Optional[Callable] = None
        self.model = None
        
    def initialize(self):
        if not os.path.exists(self.model_path):
            print(f"VOSK Model not found at {self.model_path}. Voice listener disabled.")
            return False
            
        try:
            print("Loading VOSK Model...")
            self.model = Model(self.model_path)
            print("VOSK Model loaded.")
            return True
        except Exception as e:
            print(f"Failed to load VOSK model: {e}")
            return False

    def on_wake_word(self, callback: Callable):
        self.callback = callback

    def start(self):
        if not self.model:
            if not self.initialize():
                return

        self.is_running = True
        
        # Run in a separate thread usually, but here we can define the blocking loop
        # and let main.py run it in a Thread.
        import threading
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        print("Voice Listener Thread Started.")

    def stop(self):
        self.is_running = False

    def _listen_loop(self):
        try:
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
            stream.start_stream()
            
            rec = KaldiRecognizer(self.model, 16000)
            
            print(f"Listening for wake word: '{self.wake_word}'...")
            
            while self.is_running:
                data = stream.read(4000, exception_on_overflow=False)
                if len(data) == 0:
                    break
                    
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").lower()
                    
                    if text:
                        print(f"[DEBUG] VOSK Heard: '{text}'")
                    
                    # Phonetic variations and High-Fidelity Names
                    # "Jarvis", "Computer", "Nova" are recognized very clearly by VOSK.
                    triggers = [
                        "karan", "kuren", "current",                # Original
                        "jarvis", "harvest",                        # Jarvis variations
                        "computer",                                 # Star Trek
                        "nova", "over",                             # Nova (sometimes heard as over)
                        "atlas", "alice",                           # Other distinct names
                        "hey k", "okay k"                           # Short commands
                    ]
                    if any(trigger in text for trigger in triggers):
                        print(f"WAKE WORD DETECTED: {text}")
                        if self.callback:
                            # Run callback (careful with async/sync bridge)
                            # Ideally callback schedules something on the main loop
                            self.callback()
                            
        except Exception as e:
            print(f"Voice Listener Error: {e}")
            
