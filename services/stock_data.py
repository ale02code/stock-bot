import yfinance as yf

def fetch_stock_data():
  df = yf.download("SPY", period="7d", interval="1d")
  return df.head()

print(fetch_stock_data())