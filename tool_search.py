import os
from dotenv import load_dotenv
from tavily import TavilyClient

# Load the secret key
load_dotenv()

def get_market_news(query):
    print(f"--- Searching for: {query} ---")
    
    # Initialize Tavily
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY not found in .env"
        
    tavily = TavilyClient(api_key=api_key)
    
    # Search!
    # "search_depth='basic'" is faster and cheaper. 
    # "include_domains" can be used to restrict to finance sites, but we'll leave it open for now.
    response = tavily.search(query=query, max_results=3, search_depth="basic")
    
    # Format the results for the LLM
    # We need: Title, URL, and a short Content snippet
    results_text = []
    
    for i, result in enumerate(response['results']):
        # We add [1], [2] here so the LLM can reference them later
        entry = f"[{i+1}] Title: {result['title']}\n    Link: {result['url']}\n    Snippet: {result['content']}\n"
        results_text.append(entry)
    
    return "\n".join(results_text)

if __name__ == "__main__":
    news = get_market_news("Why is NVDA stock up today?")
    print(news)