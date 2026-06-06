import yfinance as yf

tickers = ["RELIANCE.NS", "TCS.NS", "SUZLON.NS", "YESBANK.NS", "ZOMATO.NS"]
data = yf.download(tickers, period="1d", threads=True)
print(data.columns)

valid = []
for ticker in tickers:
    try:
        price = data["Close"][ticker].iloc[-1]
        import math
        if not math.isnan(price):
            print(f"{ticker}: {price}")
            if price <= 50:
                valid.append(ticker)
    except Exception as e:
        print(f"Error {ticker}: {e}")

print("Valid:", valid)
