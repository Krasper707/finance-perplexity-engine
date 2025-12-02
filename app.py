import os
import yfinance as yf
from dotenv import load_dotenv
from tavily import TavilyClient
from openai import OpenAI
import pandas as pd
import time
import asyncio 
# The Cache: Stores { "TICKER": { "report": "...", "time": 12345 } }
REPORT_CACHE = {}
CACHE_DURATION = 60 # seconds
load_dotenv()

# 2. Setup Clients
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
llm_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
def calculate_rsi(data, window=14):
    """Calculates the Relative Strength Index (Technical Indicator)."""
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.iloc[-1]

async def get_stock_data_async(ticker):
    print("   -> Fetching Stocks...")
    def fetch():
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        return hist
    
    hist = await asyncio.to_thread(fetch)
    
    if hist.empty: return "No data."
    
    # Math logic
    current = hist['Close'].iloc[-1]
    prev = hist['Close'].iloc[-2]
    change = ((current - prev) / prev) * 100
    rsi = calculate_rsi(hist)
    
    return f"Price: ${current:.2f}\nChange: {change:.2f}%\nRSI: {rsi:.2f}"


async def get_news_async(ticker):
    print("   -> Fetching News...")
    def fetch():
        return tavily_client.search(query=f"Why is {ticker} moving?", topic="news", max_results=3)
    
    response = await asyncio.to_thread(fetch)
    
    # Format
    context = ""
    sources = []
    for i, res in enumerate(response['results']):
        context += f"[{i+1}] {res['title']}: {res['content']}\n"
        sources.append({"id": i+1, "title": res['title'], "url": res['url']})
        
    return context, sources
async def generate_report(ticker):
    start = time.time()
    
    # Check Cache
    if ticker in REPORT_CACHE and (start - REPORT_CACHE[ticker]['time'] < CACHE_DURATION):
        print("⚡ CACHE HIT")
        return REPORT_CACHE[ticker]['report']

    print(f"🚀 Analyzing {ticker}...")

    # --- THE MAGIC: RUN TOGETHER ---
    # This launches both functions at the exact same moment
    stock_task = get_stock_data_async(ticker)
    news_task = get_news_async(ticker)
    
    # Wait for both to finish
    price_data, (news_context, sources) = await asyncio.gather(stock_task, news_task)
    
    print(f"✅ Data collected in {time.time() - start:.2f}s")

    # LLM Call (Standard)
    system = "You are a Financial Analyst. Cite sources [1]. Combine technicals and news."
    prompt = f"TECHNICALS:\n{price_data}\n\nNEWS:\n{news_context}"
    
    response = llm_client.chat.completions.create(
        model= "openai/gpt-oss-20b:free",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    )
    
    final = response.choices[0].message.content
    
    # Update Cache
    REPORT_CACHE[ticker] = {"report": final, "time": time.time()}
    return final

# --- RUN LOOP ---
if __name__ == "__main__":
    while True:
        ticker = input("\nTicker: ").strip().upper()
        if not ticker: break
        
        # Asyncio entry point
        report = asyncio.run(generate_report(ticker))
        print("\n" + report)
