import sys
import os

import yfinance as yf

from charts import build_price_chart_png

import json

print("Téléchargement des données financières avec yfinance")

with open('yfinance-stocks.json', 'r') as f:
    assets = json.load(f)
    
# get output dir from argv

interval = sys.argv[1] if len(sys.argv) > 1 else "1d"
output_dir = sys.argv[2] if len(sys.argv) > 2 else interval
# create output dir as subdirectory of `data` dir if it doesn't exist
output_dir = os.path.join("data", output_dir)
if not os.path.exists(output_dir):
    os.makedirs(output_dir)


for asset in assets:
    try:
        ticker = asset['yfinance_ticker']
        name = asset['name']
        print(f"Traitement de {name} ({ticker})")
        chart_path = build_price_chart_png(ticker, interval=interval, candles_count=100)
        if chart_path:
            print(f"Graphique généré pour {name} ({ticker}) : {chart_path}")
            os.rename(chart_path, os.path.join(output_dir, f"{ticker}_{name}.png"))
        
    except KeyboardInterrupt as e:
        print("Interruption par l'utilisateur, arrêt du script.")
        sys.exit(0)
        
    except Exception as e:
        print(f"Erreur lors du traitement de {asset['name']} ({ticker}): {e}")
        
        
    