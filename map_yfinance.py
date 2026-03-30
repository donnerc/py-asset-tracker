import json

with open("stocks_with_exchanges.json", "r", encoding="utf-8") as f:
    stocks = json.load(f)

# Mapping for Euronext Amsterdam
AMSTERDAM_TICKERS = {'ASML', 'INGA', 'HEIO', 'PHIA', 'SHELL', 'AS', 'AD', 'WKL', 'KPN', 'RAND', 'URW'}
# Mapping for Euronext Brussels
BRUSSELS_TICKERS = {'ABI', 'UCB', 'SOLB', 'KBC', 'BEFB', 'VGP'}

def get_yfinance_ticker(exchange, yuh_ticker):
    # Special cases
    if yuh_ticker == 'BRK/B':
        return 'BRK-B'
    if yuh_ticker == 'BP.':
        return 'BP.L'
    if yuh_ticker == 'AF FP':
        return 'AF.PA'
    
    # Generic mapping based on exchange
    if exchange == 'SIX':
        return f"{yuh_ticker}.SW"
    if exchange == 'XETR':
        return f"{yuh_ticker}.DE"
    if exchange == 'LSE':
        return f"{yuh_ticker}.L"
    if exchange == 'MIL':
        return f"{yuh_ticker}.MI"
    if exchange == 'BME':
        return f"{yuh_ticker}.MC"
    if exchange in ('NYSE', 'NASDAQ'):
        return yuh_ticker
    if exchange == 'EURONEXT':
        if yuh_ticker in AMSTERDAM_TICKERS:
            return f"{yuh_ticker}.AS"
        elif yuh_ticker in BRUSSELS_TICKERS:
            return f"{yuh_ticker}.BR"
        else:
            return f"{yuh_ticker}.PA" # Default to Paris
    
    return yuh_ticker

yfinance_stocks = []
for stock in stocks:
    yf_ticker = get_yfinance_ticker(stock['exchange'], stock['yuh_ticker'])
    yfinance_stocks.append({
        "yuh_ticker": stock['yuh_ticker'],
        "yfinance_ticker": yf_ticker,
        "name": stock['name']
    })

with open("yfinance-stocks.json", "w", encoding="utf-8") as f:
    json.dump(yfinance_stocks, f, ensure_ascii=False, indent=2)

print(f"Created yfinance-stocks.json with {len(yfinance_stocks)} entries")
