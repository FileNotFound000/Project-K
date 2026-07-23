import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from app.services.agent import AgentService
import asyncio
import json
import re
import sys
from app.core.logger import get_logger

logger = get_logger(__name__)

async def search_and_scrape(query: str, max_results: int = 3) -> str:
    """Searches the web and scrapes content from top results."""
    logger.info(f"Searching for: {query}")
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        with DDGS() as ddgs:
            # Add time='y' for past year to ensure relevance, or leave empty for all time
            ddgs_results = list(ddgs.text(query, max_results=max_results))
            
            for r in ddgs_results:
                url = r['href']
                title = r['title']
                snippet = r.get('body', '')
                
                # Basic filtering
                if "researchgate.net" in url or ".pdf" in url:
                    results.append(f"Source: {title} ({url})\nSnippet: {snippet}\n(Skipped scraping PDF/Restricted)\n---")
                    continue
                    
                logger.info(f"Scraping: {url}")
                
                content_to_add = ""
                try:
                    # Timeout to prevent hanging
                    response = requests.get(url, headers=headers, timeout=5)
                    # Use apparent_encoding if encoding is missing or ISO-8859-1 (often wrong default)
                    if not response.encoding or response.encoding.lower() == 'iso-8859-1':
                        response.encoding = response.apparent_encoding
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Remove script and style elements
                        for script in soup(["script", "style", "nav", "footer", "header"]):
                            script.decompose()
                            
                        # Extract text from paragraphs
                        paragraphs = soup.find_all('p')
                        text_content = "\n".join([p.get_text() for p in paragraphs])
                        
                        # Check for "blocked" content or empty
                        if len(text_content) < 100 or "access to this paper" in text_content.lower():
                             content_to_add = snippet
                        else:
                            # Truncate to avoid token limits (approx 2000 chars)
                            content_to_add = text_content[:2000]
                    else:
                        content_to_add = snippet
                        
                except Exception as e:
                    logger.error(f"Failed to scrape {url}: {e}")
                    content_to_add = snippet
                
                results.append(f"Source: {title} ({url})\nContent:\n{content_to_add}\n---")
                    
    except Exception as e:
        return f"Error during research: {str(e)}"

    if not results:
        return "No useful information found."

    return "\n\n".join(results)

async def generate_research_report(topic: str, llm_service: AgentService, session_id: str):
    """
    Orchestrates a Deep Research Loop:
    1. Plan: Generate search queries
    2. Execute: Search & Scrape
    3. Analyze & Refine: Check if enough info, else repeat
    4. Report: Write final summary
    """
    
    # --- Step 1: Planning ---
    yield {"text": f"🧠 **Planning** research strategy for: '{topic}'...\n\n"}
    
    planning_prompt = f"""
    You are a Senior Research Analyst.
    Topic: {topic}
    
    Generate 3 specific search queries to gather comprehensive information on this topic.
    Return ONLY a JSON array of strings. Example: ["query 1", "query 2", "query 3"]
    """
    
    plan_response = ""
    async for chunk in llm_service.generate_response_stream(planning_prompt, session_id=session_id, save_user_message=False):
         if "text" in chunk:
             plan_response += chunk["text"]
    
    # Extract JSON
    queries = []
    try:
        # Simple extraction for list
        match = re.search(r'\[.*\]', plan_response, re.DOTALL)
        if match:
            queries = json.loads(match.group())
        else:
            queries = [topic] # Fallback
    except:
        queries = [topic] # Fallback
        
    yield {"text": f"🔎 **Queries generated**: {', '.join(queries[:3])}...\n\n"}
    
    # --- Step 2: Execution (Sequential for now to respect rate limits) ---
    aggregated_context = ""
    
    for i, query in enumerate(queries[:3]): # Start with max 3 queries
        yield {"text": f"🌐 **Searching**: '{query}'...\n"}
        search_result = await search_and_scrape(query, max_results=2)
        aggregated_context += f"\n\n### Results for '{query}'\n{search_result}"
        
    # --- Step 3: Analysis & Reporting ---
    yield {"text": f"📚 **Analyzing** {len(aggregated_context)} chars of data and writing report...\n\n"}
    
    final_prompt = f"""
    You are an Expert Research Analyst.
    Topic: {topic}
    
    Below is the raw data gathered from multiple searches:
    {aggregated_context}
    
    Write a comprehensive, professional research report.
    
    Guidelines:
    1. **Structure**: Use Header 1 for Title, Header 2 for sections.
    2. **Citations**: You MUST cite your sources. Use [Source Title](URL) format wherever specific claims are made.
    3. **Tone**: Objective, detailed, and clear.
    4. **Synthesis**: Do not just list results; synthesize them into a coherent narrative.
    5. If there are conflicting facts, note them.
    
    Begin the report now.
    """
    
    async for chunk in llm_service.generate_response_stream(final_prompt, session_id=session_id, save_user_message=False):
        if "text" in chunk:
            yield chunk
