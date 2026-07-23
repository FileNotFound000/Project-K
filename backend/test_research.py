import sys
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import asyncio
from app.services.research import generate_research_report

class MockAgentService:
    async def generate_response_stream(self, prompt, session_id, save_user_message=False):
        print(f"\n[MockLLM] Received Prompt (truncated): {prompt[:50]}...")
        
        if "Generate 3 specific search queries" in prompt:
            # Planning phase
            yield {"text": '["history of internet", "who invented the web", "arpanet origins"]'}
        elif "Write a comprehensive" in prompt:
            # Reporting phase
            yield {"text": "# Comprehensive Report\n\nThe internet started with ARPANET..."}
        else:
            yield {"text": "Unknown prompt"}

async def main():
    print("Testing Deep Research Loop with Mock LLM...")
    
    mock_llm = MockAgentService()
    
    print("\n--- STARTING STREAM ---\n")
    
    async for chunk in generate_research_report("history of internet", mock_llm, "test_session"):
        if "text" in chunk:
            print(chunk["text"], end="", flush=True)
            
    print("\n\n--- TEST COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(main())
