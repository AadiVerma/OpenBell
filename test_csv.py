import urllib.request
import csv
import io
url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    raw = resp.read().decode("utf-8", errors="replace")

reader = csv.DictReader(io.StringIO(raw))
for i, row in enumerate(reader):
    if i < 2:
        print(row)
