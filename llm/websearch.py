import os
from typing import List, Dict, Any, Optional

def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Searches the web with DuckDuckGo (ddgs), the free default that needs no key.
    If the tavily provider is selected and a key exists, Tavily is used.
    Returns a list of dicts: [{"title": ..., "url": ..., "snippet": ...}]
    """
    provider = os.getenv("WEB_SEARCH_PROVIDER", "ddgs").lower()
    tavily_key = os.getenv("TAVILY_API_KEY")

    results = []

    # Option 1: Tavily when requested and a key exists
    if provider == "tavily" and tavily_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            res = client.search(query=query, max_results=max_results)
            for item in res.get("results", []):
                snippet = (item.get("content") or "")[:500]
                results.append({
                    "title": item.get("title", "No Title"),
                    "url": item.get("url", ""),
                    "snippet": snippet
                })
            return results
        except Exception:
            pass # fall back to ddgs on error

    # Option 2: default DDGS (DuckDuckGo)
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
            for item in raw_results:
                snippet = (item.get("body") or "")[:500]
                results.append({
                    "title": item.get("title", "No Title"),
                    "url": item.get("href", ""),
                    "snippet": snippet
                })
    except Exception as e:
        print(f"Web search warning: {e}")

    return results

def format_search_results_for_llm(results: List[Dict[str, str]]) -> str:
    """Formats search results as numbered text to add to the LLM context."""
    if not results:
        return "No web search results were found."
    
    formatted_items = []
    for idx, r in enumerate(results, start=1):
        formatted_items.append(
            f"[{idx}] {r['title']}\nLink: {r['url']}\nSnippet: {r['snippet']}"
        )
    return "\n\n".join(formatted_items)
