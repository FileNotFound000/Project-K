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
                # For common apps, we might need a mapping or just try the name
                os.startfile(app_name)
                return f"Opening {app_name}"
            else:
                return "App launching only supported on Windows for now."
        except Exception as e:
            # Try using pyautogui to press win key and type
            try:
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

    def interact(self, action: str, **kwargs):
        """
        Generic interaction: "type", "press", "hotkey"
        """
        try:
            if action == "type":
                text = kwargs.get("text", "")
                interval = kwargs.get("interval", 0.05)
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
