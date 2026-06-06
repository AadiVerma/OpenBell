import yfinance as yf
from app.services.seed import fetch_index_tickers

tickers_dict = fetch_index_tickers("NIFTY500")
tickers = [t["ticker"] for t in tickers_dict]
print(f"Total tickers: {len(tickers)}")

data = yf.download(tickers, period="1d", threads=True)
valid = []
for t in tickers_dict:
    ticker = t["ticker"]
    try:
        price = data["Close"][ticker].iloc[-1]
        import math
        if not math.isnan(price) and price <= 100:
            valid.append((ticker, price))
    except Exception as e:
        pass
print(valid)
