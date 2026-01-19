import pyautogui
import os
import platform
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

class SystemControlService:
    def __init__(self):
        # Fail-safe: moving mouse to corner will throw exception
        pyautogui.FAILSAFE = True
        self.system = platform.system()

    def set_volume(self, level: int):
        """
        Set system volume to a specific level (0-100).
        """
        try:
            if self.system == "Windows":
                devices = AudioUtilities.GetSpeakers()
                # interface = devices.Activate(
                #     IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                # volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume = devices.EndpointVolume
                
                # Volume range is usually -65.25 to 0.0
                # We need to map 0-100 to scalar 0.0-1.0
                scalar_volume = max(0.0, min(1.0, level / 100.0))
                volume.SetMasterVolumeLevelScalar(scalar_volume, None)
                return f"Volume set to {level}%"
            else:
                return "Volume control only supported on Windows for now."
        except Exception as e:
            print(f"Error setting volume: {e}")
            return f"Error setting volume: {str(e)}"

    def set_mute(self, mute: bool):
        """
        Set mute state (True for mute, False for unmute).
        """
        try:
            if self.system == "Windows":
                devices = AudioUtilities.GetSpeakers()
                volume = devices.EndpointVolume
                
                volume.SetMute(1 if mute else 0, None)
                return "Volume muted" if mute else "Volume unmuted"
            else:
                return "Mute control only supported on Windows for now."
        except Exception as e:
            print(f"Error setting mute: {e}")
            return f"Error setting mute: {str(e)}"

    def open_application(self, app_name: str):
        """
        Open an application.
        """
        try:
            if self.system == "Windows":
                # Simple startfile (works for registered apps and paths)
                # Special handling for opening folders in VS Code
                if "code" in app_name.lower() and os.path.isdir(app_name.split()[-1]):
                     # If the request is "code C:/path", execute it as a command
                     os.system(app_name)
                     return f"Running command: {app_name}"
                
                # Check if it's a folder path prompt
                if os.path.isdir(app_name):
                    os.startfile(app_name)
                    return f"Opened folder: {app_name}"

                os.startfile(app_name)
                return f"Opening {app_name}"
            else:
                return "App launching only supported on Windows for now."
        except Exception as e:
            # Fallback for common web apps or specific failures
            try:
                if "youtube" in app_name.lower():
                    import webbrowser
                    # If the app_name looks like a URL or a complicated query, try to respect it
                    if "http" in app_name or ".com" in app_name:
                         # It's likely a URL passed as app_name
                         url = app_name
                         if not url.startswith("http"):
                             url = "https://" + url.strip()
                         # Clean up "chrome " prefix if agent added it
                         url = url.replace("https://chrome ", "https://") 
                         webbrowser.open(url)
                         return f"Opened YouTube URL: {url}"
                    else:
                        webbrowser.open("https://www.youtube.com")
                        return "Opened YouTube in browser."
                elif "spotify" in app_name.lower() and "http" not in app_name: 
                    # Try spotify protocol or web
                    import webbrowser
                    webbrowser.open("https://open.spotify.com")
                    return "Opened Spotify in browser."
                
                # Try using pyautogui to press win key and type
                pyautogui.press('win')
                pyautogui.sleep(0.5)
                pyautogui.write(app_name)
                pyautogui.sleep(0.5)
                pyautogui.press('enter')
                return f"Attempting to open {app_name} via Start Menu"
            except Exception as e2:
                print(f"Error opening app: {e2}")
                return f"Error opening app: {str(e2)}"

        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return None

    def media_control(self, action: str):
        """
        Control media playback.
        actions: "play_pause", "next", "prev", "stop"
        """
        key_map = {
            "play_pause": "playpause",
            "next": "nexttrack",
            "prev": "prevtrack",
            "stop": "stop"
        }
        key = key_map.get(action)
        if key:
            pyautogui.press(key)
            return f"Media action executed: {action}"
        return f"Unknown media action: {action}"

    def set_brightness(self, level: int):
        """
        Set screen brightness (0-100).
        """
        try:
            import screen_brightness_control as sbc
            sbc.set_brightness(level)
            return f"Brightness set to {level}%"
        except ImportError:
            return "Error: screen-brightness-control module not installed."
        except Exception as e:
            return f"Error setting brightness: {e}"

    def system_power(self, action: str):
        """
        Power actions: "shutdown", "restart", "sleep", "lock"
        """
        if self.system == "Windows":
            if action == "shutdown":
                os.system("shutdown /s /t 10") # 10s delay to cancel
                return "Shutting down in 10 seconds. Run 'shutdown /a' to abort."
            elif action == "restart":
                os.system("shutdown /r /t 10")
                return "Restarting in 10 seconds."
            elif action == "sleep":
                os.system("rundll32.dll powrprof.dll,SetSuspendState 0,1,0")
                return "Going to sleep..."
            elif action == "lock":
                os.system("rundll32.dll user32.dll,LockWorkStation")
                return "Locking workstation."
        return f"Power action {action} not supported or failed."

    def window_control(self, action: str):
        """
        Window actions: "minimize", "maximize", "restore"
        """
        if action == "minimize":
            pyautogui.hotkey('win', 'down')
            pyautogui.hotkey('win', 'down') # Twice often needed to fully minimize
            return "Window minimized"
        elif action == "maximize":
            pyautogui.hotkey('win', 'up')
            return "Window maximized"
        return f"Unknown window action: {action}"

    def write_file(self, path: str, content: str):
        """
        Write content to a file.
        """
        try:
            # If path is just a filename, use CWD or a safe default? 
            # Current CWD is usually .../backend. We want to write to Project Root.
            if not os.path.isabs(path):
                # Check settings for a custom workspace path
                try:
                    from app.services.settings import SettingsService
                    settings = SettingsService().load_settings()
                    workspace_path = settings.get("workspace_path")
                    if workspace_path and os.path.isdir(workspace_path):
                        path = os.path.join(workspace_path, path)
                    else:
                        # Fallback to smart project root detection
                        cwd = os.getcwd()
                        if os.path.basename(cwd) == "backend":
                            base_path = os.path.dirname(cwd) # ../
                            path = os.path.join(base_path, path)
                        else:
                            path = os.path.abspath(path)
                except Exception:
                     # Fallback if imports fail
                    cwd = os.getcwd()
                    if os.path.basename(cwd) == "backend":
                        base_path = os.path.dirname(cwd)
                        path = os.path.join(base_path, path)
                    else:
                        path = os.path.abspath(path)
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {path}"
        except Exception as e:
            return f"Error writing file: {e}"

    def read_file(self, path: str):
        """Read content from a file."""
        try:
             # Normalize path logic (reuse write_file logic if possible, or duplicate for safety)
            if not os.path.isabs(path):
                 # Smart fallback logic
                 try:
                    from app.services.settings import SettingsService
                    settings = SettingsService().load_settings()
                    workspace_path = settings.get("workspace_path")
                    if workspace_path and os.path.isdir(workspace_path):
                         path = os.path.join(workspace_path, path)
                    else:
                        cwd = os.getcwd()
                        if os.path.basename(cwd) == "backend":
                            base_path = os.path.dirname(cwd)
                            path = os.path.join(base_path, path)
                        else:
                            path = os.path.abspath(path)
                 except:
                    cwd = os.getcwd()
                    if os.path.basename(cwd) == "backend":
                         path = os.path.join(os.path.dirname(cwd), path)
                    else:
                         path = os.path.abspath(path)

            if not os.path.exists(path):
                return f"Error: File not found at {path}"
            
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

    def list_files(self, path: str = "."):
        """List files in a directory."""
        try:
            # Normalize path
            if not os.path.isabs(path):
                 try:
                    from app.services.settings import SettingsService
                    settings = SettingsService().load_settings()
                    workspace_path = settings.get("workspace_path")
                    if workspace_path and os.path.isdir(workspace_path):
                         path = os.path.join(workspace_path, path)
                    else:
                        cwd = os.getcwd()
                        if os.path.basename(cwd) == "backend":
                            base_path = os.path.dirname(cwd)
                            path = os.path.join(base_path, path)
                        else:
                            path = os.path.abspath(path)
                 except:
                     pass # default to abs path or cwd

            if not os.path.exists(path):
                return f"Error: Directory not found at {path}"
                
            items = os.listdir(path)
            # Add type info
            result = []
            for item in items:
                full_item = os.path.join(path, item)
                kind = "DIR" if os.path.isdir(full_item) else "FILE"
                result.append(f"[{kind}] {item}")
            return "\n".join(result)
        except Exception as e:
            return f"Error listing files: {e}"

    def replace_text(self, path: str, search_text: str, replace_text: str):
        """Replace text in a file."""
        try:
            content = self.read_file(path)
            if content.startswith("Error"):
                return content
            
            if search_text not in content:
                return "Error: Search text not found in file."
            
            new_content = content.replace(search_text, replace_text)
            
            # Reuse logic to get absolute path for writing
            # For simplicity, since read_file succeeded, we can probably trust the path resolution inside read_file 
            # BUT read_file resolved it internally. We need to resolve it again OR extract the resolution logic.
            # To be safe, let's just use the same resolution logic.
            
            # ... (Full resolution logic again) ...
            if not os.path.isabs(path):
                 try:
                    from app.services.settings import SettingsService
                    settings = SettingsService().load_settings()
                    workspace_path = settings.get("workspace_path")
                    if workspace_path and os.path.isdir(workspace_path):
                         path = os.path.join(workspace_path, path)
                    else:
                        cwd = os.getcwd()
                        if os.path.basename(cwd) == "backend":
                            base_path = os.path.dirname(cwd)
                            path = os.path.join(base_path, path)
                        else:
                             path = os.path.abspath(path)
                 except:
                    cwd = os.getcwd()
                    if os.path.basename(cwd) == "backend":
                         path = os.path.join(os.path.dirname(cwd), path)
                    else:
                         path = os.path.abspath(path)

            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
                
            return "Successfully replaced text."
        except Exception as e:
            return f"Error replacing text: {e}"

    def interact(self, action: str, **kwargs):
        """
        Generic interaction: "type", "press", "hotkey"
        """
        try:
            if action == "type":
                text = kwargs.get("text", "")
                interval = kwargs.get("interval", 0.005) # Faster typing
                pyautogui.write(text, interval=interval)
                return f"Typed: {text}"
            elif action == "press":
                key = kwargs.get("key")
                pyautogui.press(key)
                return f"Pressed: {key}"
            elif action == "hotkey":
                keys = kwargs.get("keys", []) # List of keys e.g. ['ctrl', 'c']
                pyautogui.hotkey(*keys)
                return f"Hotkey pressed: {keys}"
            elif action == "click":
                x = kwargs.get("x")
                y = kwargs.get("y")
                if x is not None and y is not None:
                    pyautogui.click(x, y)
                    return f"Clicked at ({x}, {y})"
                return "Error: Coordinates x and y required for click."
        except Exception as e:
            return f"Interaction error: {e}"
        return f"Unknown interaction: {action}"
