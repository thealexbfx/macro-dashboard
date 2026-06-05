import yfinance as yf
import pandas as pd

def print_last_4_closing_prices(ticker_symbol="GBPUSD=X"):
    data = yf.download(ticker_symbol, period="7d", interval="1d", auto_adjust=False)
    
    if data.empty:
        print("No data fetched. Please check ticker or internet connection.")
        return
    
    close_data = data['Close']
    last_4_closes = close_data.tail(4)
    
    print(f"Last 4 closing prices for {ticker_symbol}:")
    for date, price in last_4_closes.items():
        date_str = date.date() if hasattr(date, 'date') else date
        print(f"{date_str}: {price:.5f}")

if __name__ == "__main__":
    print_last_4_closing_prices()
