"""
web_search.py
-------------
Jab documents mein answer nahi milta, ya user ko latest/real-time
information chahiye hoti hai (jaise aaj ka news, current price),
tab yeh module Tavily API se web search karke result laata hai.

Tavily ka free tier: 1000 searches/month - personal use ke liye kaafi hai.
Free API key: https://tavily.com se milti hai.
"""

from tavily import TavilyClient
import config


def web_search(query: str, max_results: int = None):
    """Web search karke top results (title + summary + link) return karta hai."""
    if not config.ALLOW_CLOUD_PROVIDERS:
        return "External web search disabled hai kyunki local-only privacy mode enabled hai."
    if not config.TAVILY_API_KEY:
        return "Web search available nahi hai - TAVILY_API_KEY .env file mein daalo."

    max_results = max_results or config.WEB_SEARCH_RESULTS
    client = TavilyClient(api_key=config.TAVILY_API_KEY)

    response = client.search(
        query=query,
        max_results=max_results,
        search_depth="advanced",
    )

    formatted_results = []
    for r in response.get("results", []):
        formatted_results.append(
            f"Source: {r['url']}\nTitle: {r['title']}\nContent: {r['content']}\n"
        )

    return "\n---\n".join(formatted_results) if formatted_results else "Kuch nahi mila."
