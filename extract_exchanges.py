import re
import json
import subprocess

url = "https://www.yuh.com/fr/app/invest/stocks/"
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

result = subprocess.run(["curl", "-s", "-L", "-A", user_agent, url], capture_output=True, text=True)
html = result.stdout

matches = re.findall(r'"name":\s*"([^"]*):([^"]*)",\s*"displayName":\s*"([^"]*)"', html)

stocks = []
for exchange, ticker, name in matches:
    stocks.append({
        "yuh_ticker": ticker,
        "exchange": exchange,
        "name": name
    })

# Remove duplicates
seen = set()
unique_stocks = []
for stock in stocks:
    key = (stock["exchange"], stock["yuh_ticker"])
    if key not in seen:
        unique_stocks.append(stock)
        seen.add(key)

with open("stocks_with_exchanges.json", "w", encoding="utf-8") as f:
    json.dump(unique_stocks, f, ensure_ascii=False, indent=2)

print(f"Extracted {len(unique_stocks)} stocks with exchanges")
