"""
Optional enrichment: use the Parallel Search API to verify whether a
real-world reference (person/brand) actually exists and gather a short
snippet of context, before the Legal Clearance agent reasons about it.
If PARALLEL_API_KEY is unset, callers should skip enrichment rather than
fake a result — see legal_clearance.py integration point.
"""
import os
import requests

PARALLEL_SEARCH_URL = "https://api.parallel.ai/v1/search"


def search_reference(query: str) -> str | None:
    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        return None
    response = requests.post(
        PARALLEL_SEARCH_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"query": query, "max_results": 3},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results", [])
    if not results:
        return None
    return " ".join(r.get("snippet", "") for r in results[:2])
