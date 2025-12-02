import yfinance as yf
def get_stock_data(ticker):
    print(f"--- Fetching data for {ticker} ---")
    stock = yf.Ticker(ticker)
    
    history = stock.history(period="1mo")
    
    if history.empty:
        return "Error: NO DATA FOUND"
    recent_data=history.tail(5)
    output=[]
    for date, row in recent_data.iterrows():
        date_str = date.strftime('%Y-%m-%d')
        price = round(row['Close'], 2)
        output.append(f"Date: {date_str}, Close: ${price}")
    
    return "\n".join(output)

if __name__ == "__main__":
    result = get_stock_data("AAPL")
    print(result)
