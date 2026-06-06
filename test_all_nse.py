import urllib.request
import csv
import io
import yfinance as yf
import time

url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    raw = resp.read().decode("utf-8", errors="replace")

reader = csv.DictReader(io.StringIO(raw))
tickers = []
for row in reader:
    symbol = (row.get("SYMBOL") or "").strip()
    if symbol:
        tickers.append(f"{symbol}.NS")

print(f"Total NSE securities: {len(tickers)}")

start = time.time()
data = yf.download(tickers, period="1d", threads=True)
print(f"Time taken to fetch {len(tickers)} tickers: {time.time() - start:.2f}s")
