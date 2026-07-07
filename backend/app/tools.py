"""
Simple tools available to agents.

Kept intentionally minimal for a prototype: one web search tool backed by
duckduckgo-search (no API key required). Swap this out for a real search
provider (Tavily, Bing, Google CSE, etc.) for production use.
"""
from typing import List, Dict


def web_search(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """Run a web search and return a list of {title, url, snippet} dicts."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return [{"title": "search unavailable", "url": "", "snippet": ""}]

    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    }
                )
    except Exception as e:
        results.append({"title": "search error", "url": "", "snippet": str(e)})
    return results


def format_search_results(results: List[Dict[str, str]]) -> str:
    lines = []
    for r in results:
        lines.append(f"- {r['title']}: {r['snippet']} ({r['url']})")
    return "\n".join(lines) if lines else "No results found."
