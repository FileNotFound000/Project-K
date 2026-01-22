import asyncio
from typing import List, Dict, Any

class WorkflowService:
    def __init__(self, system_control_service):
        self.system_control = system_control_service
        
        # Define default workflows
        # In a future version, these could be loaded from a JSON file
        self.workflows: Dict[str, List[Dict[str, Any]]] = {
            "work_mode": [
                {"action": "set_volume", "level": 30},
                {"action": "open_application", "app_name": "code ."}, # VS Code in current dir
                {"action": "open_application", "app_name": "http://localhost:3000"}, # Frontend
                {"action": "open_application", "app_name": "http://localhost:8000/docs"}, # Backend Docs
                {"action": "open_application", "app_name": "https://open.spotify.com/playlist/37i9dQZF1DX6tGWj8KW8Ww"} # Focus Music
            ],
            "gaming_mode": [
                {"action": "set_volume", "level": 100},
                {"action": "open_application", "app_name": "steam"}
            ],
            "focus_mode": [
                 {"action": "set_volume", "level": 50},
                 {"action": "open_application", "app_name": "https://www.youtube.com/watch?v=CBSlu_VMS9U"} # Lofi Girl
            ],
             "sleep_mode": [
                 {"action": "set_volume", "level": 0},
                 {"action": "media", "action_type": "stop"},
                 {"action": "power", "action_type": "sleep"}
            ]
        }

    def get_available_workflows(self) -> List[str]:
        return list(self.workflows.keys())

    async def execute_workflow(self, workflow_name: str) -> str:
        """
        Execute a sequence of actions for a given workflow.
        """
        workflow_name = workflow_name.lower().replace(" ", "_")
        steps = self.workflows.get(workflow_name)
        
        if not steps:
            # Fuzzy match or fallback?
            return f"Error: Workflow '{workflow_name}' not found. Available: {', '.join(self.get_available_workflows())}"
            
        results = []
        results.append(f"Activating {workflow_name}...")
        
        for step in steps:
            action = step.get("action")
            
            try:
                if action == "open_application":
                    res = self.system_control.open_application(step.get("app_name"))
                    results.append(res)
                elif action == "set_volume":
                    res = self.system_control.set_volume(step.get("level"))
                    results.append(res)
                elif action == "media":
                    res = self.system_control.media_control(step.get("action_type"))
                    results.append(res)
                elif action == "power":
                    res = self.system_control.system_power(step.get("action_type"))
                    results.append(res)
                elif action == "wait":
                    sec = step.get("seconds", 1)
                    await asyncio.sleep(sec)
                    results.append(f"Waited {sec}s")
                else:
                    results.append(f"Unknown action: {action}")
                
                # Small delay between steps to prevent system choke
                await asyncio.sleep(0.5)
                
            except Exception as e:
                results.append(f"Step failed ({action}): {e}")
                
        return "\n".join(filter(None, results))
