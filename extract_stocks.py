import re
import json
import subprocess

url = "https://www.yuh.com/fr/app/invest/stocks/"
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Fetch HTML
result = subprocess.run(["curl", "-s", "-L", "-A", user_agent, url], capture_output=True, text=True)
html = result.stdout

# Extract name and displayName
# Pattern: "name": "EXCHANGE:TICKER",\s+"displayName": "NAME"
matches = re.findall(r'"name":\s*"[^"]*:[^"]*",\s*"displayName":\s*"[^"]*"', html)

stocks = []
for match in matches:
    try:
        # Extract ticker and name
        ticker_match = re.search(r'"name":\s*"[^"]*:([^"]*)"', match)
        name_match = re.search(r'"displayName":\s*"([^"]*)"', match)
        
        if ticker_match and name_match:
            ticker = ticker_match.group(1)
            name = name_match.group(1)
            stocks.append({"ticker": ticker, "name": name})
    except Exception:
        continue

# Remove duplicates
seen = set()
unique_stocks = []
for stock in stocks:
    if stock["ticker"] not in seen:
        unique_stocks.append(stock)
        seen.add(stock["ticker"])

with open("stocks.json", "w", encoding="utf-8") as f:
    json.dump(unique_stocks, f, ensure_ascii=False, indent=2)

print(f"Extracted {len(unique_stocks)} stocks to stocks.json")
