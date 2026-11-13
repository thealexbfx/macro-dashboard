import pandas as pd
import yfinance as yf

def get_fx_data_yahoo(ticker="GBPUSD=X", start_date=None, end_date=None, adjusted=False):
    # Download historical daily data from yfinance
    data = yf.download(ticker, start=start_date, end=end_date, interval="1d", auto_adjust=False)

    if data.empty:
        return pd.DataFrame()  # Return empty DF on failure

    # If multi-index columns, select 'Close' price properly
    if isinstance(data.columns, pd.MultiIndex):
        close_data = data['Adj Close' if adjusted else 'Close'][ticker]
    else:
        close_data = data['Adj Close' if adjusted else 'Close']

    # Prepare dataframe with date and close price
    df = pd.DataFrame({
        'date': close_data.index,
        'value': close_data.values
    })

    df = df.sort_values('date').reset_index(drop=True)
    return df
