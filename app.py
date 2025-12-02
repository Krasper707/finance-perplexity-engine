import os
import yfinance as yf
from dotenv import load_dotenv
from tavily import TavilyClient
from openai import OpenAI

# 1. Load Keys
load_dotenv()

# 2. Setup Clients
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
llm_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# --- TOOL 1: GET NUMBERS ---
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        # Get 5 days of data
        hist = stock.history(period="5d")
        
        if hist.empty:
            return "No price data available."
            
        # Format it nicely for the LLM
        data_str = "Recent Price History:\n"
        for date, row in hist.iterrows():
            date_str = date.strftime('%Y-%m-%d')
            close_price = round(row['Close'], 2)
            data_str += f"- {date_str}: ${close_price}\n"
        return data_str
    except Exception as e:
        return f"Error getting stock data: {e}"

# --- TOOL 2: GET NEWS ---
def get_market_news(query):
    try:
        # Search specifically for news
        response = tavily_client.search(
            query=query, 
            search_depth="basic", 
            max_results=3,
            topic="news" # Tavily has a specific 'news' topic optimized for this
        )
        
        context = "Recent News Sources:\n"
        for i, result in enumerate(response['results']):
            # We explicitly label the Source ID [1] here
            context += f"Source [{i+1}]: {result['title']}\n"
            context += f"URL: {result['url']}\n"
            context += f"Snippet: {result['content']}\n\n"
            
        return context
    except Exception as e:
        return f"Error getting news: {e}"

# --- THE AGENT ---
def generate_report(ticker):
    print(f"\n Starting analysis for: {ticker}...")
    
    # 1. Gather Intelligence (Parallel-ish)
    print("1. Fetching Price Data...")
    price_data = get_stock_data(ticker)
    
    print("2. Searching News...")
    news_data = get_market_news(f"Why is {ticker} stock moving today?")
    
    # 2. Build the Prompt
    # We tell the LLM exactly how to behave
    system_instruction = """
    You are a Financial Analyst AI. 
    Your goal is to explain the stock trend using the provided data and news.
    
    RULES:
    1. Cite your sources using [1], [2] format strictly based on the 'Recent News Sources' provided.
    2. Do not invent URLs. Only use the ones provided.
    3. Keep the answer concise (under 150 words).
    4. First explain the price movement (from the data), then explain the cause (from the news).
    """
    
    user_prompt = f"""
    DATA:
    {price_data}
    
    NEWS:
    {news_data}
    
    Task: Analyze {ticker}.
    """
    
    # 3. Ask the Brain
    print("3. Synthesizing Report...")
    response = llm_client.chat.completions.create(
        model= "openai/gpt-oss-20b:free",

        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    return response.choices[0].message.content

if __name__ == "__main__":
    # You can change this to "TSLA", "GOOGL", "BTC-USD"
    ticker_input = "AAPL" 
    
    final_report = generate_report(ticker_input)
    
    print("\n" + "="*40)
    print(f"📊 REPORT FOR {ticker_input}")
    print("="*40 + "\n")
    print(final_report)