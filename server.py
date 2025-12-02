import os
import yfinance as yf
from dotenv import load_dotenv
from tavily import TavilyClient
from openai import OpenAI
import pandas as pd
import time
import asyncio 
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import json
from datetime import datetime

load_dotenv()
app = FastAPI(title="Finance Engine API")

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
llm_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

REPORT_CACHE = {}
CACHE_DURATION = 60

class QueryRequest(BaseModel):
    ticker: str

# --- CORE LOGIC (Same as before) ---
def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

async def get_stock_data_async(ticker):
    def fetch():
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        return hist
    
    hist = await asyncio.to_thread(fetch)
    if hist.empty: return "No data."
    
    current = hist['Close'].iloc[-1]
    prev = hist['Close'].iloc[-2]
    change = ((current - prev) / prev) * 100
    rsi = calculate_rsi(hist)
    if pd.isna(rsi): rsi = 0.0
    
    return f"Price: ${current:.2f}\nChange: {change:.2f}%\nRSI: {rsi:.2f}"

async def get_news_async(ticker):
    def fetch():
        return tavily_client.search(query=f"Why is {ticker} moving?", topic="news", max_results=3)
    
    response = await asyncio.to_thread(fetch)
    context = ""
    sources = []
    for i, res in enumerate(response['results']):
        context += f"[{i+1}] {res['title']}: {res['content']}\n"
        sources.append({"id": i+1, "title": res['title'], "url": res['url']})
    return context, sources

@app.post("/analyze")
async def analyze_stock(request: QueryRequest):
    ticker = request.ticker.upper()
    print(f"Received request for {ticker}")

    async def event_generator():
        try:
            # 1. FETCH DATA (Parallel)
            stock_task = get_stock_data_async(ticker)
            news_task = get_news_async(ticker)
            price_data, (news_context, sources) = await asyncio.gather(stock_task, news_task)

            # 2. SEND META-DATA PACKET (Instant)
            # We send this FIRST so the UI can draw the Chart/Sidebar immediately
            data_packet = {
                "type": "usage", # Metadata event
                "ticker": ticker,
                "price_data": price_data, # You might want to parse this into strict JSON later for charts
                "sources": sources
            }
            yield json.dumps(data_packet) + "\n"

            # 3. PREPARE PROMPT (Same as before)
            cur_date = datetime.now().strftime("%Y-%m-%d")
            system_prompt = f"""
            You are a Senior Quantitative Analyst at a top-tier hedge fund. 
            TODAY'S DATE: {cur_date}
            TARGET TICKER: {ticker}
            
            GUIDELINES:
            1. Identity: Professional, concise, data-driven.
            2. Format: Use Markdown. Start with 'Executive Summary'. Use tables.
            3. Citations: Use [1], [2]. IGNORE news not about {ticker}.
            4. RSI Logic: >70 Overbought, <30 Oversold.
            """
            
            user_prompt = f"TECHNICALS:\n{price_data}\n\nNEWS:\n{news_context}\n\nTASK:\nWrite the research report."

            # 4. STREAM THE LLM
            stream = llm_client.chat.completions.create(
                model="openai/gpt-oss-20b:free",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                stream=True, # <--- ENABLE STREAMING
                temperature=0.2
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    # Send text chunk
                    text_packet = {
                        "type": "content",
                        "delta": chunk.choices[0].delta.content
                    }
                    yield json.dumps(text_packet) + "\n"

        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

if __name__ == "__main__":
    import uvicorn
    print("Starting Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)