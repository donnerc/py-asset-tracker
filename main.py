import matplotlib
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import pandas as pd

import json

print("Téléchargement des données financières avec yfinance")

with open('yfinance-stocks.json', 'r') as f:
    assets = json.load(f)

for asset in assets:
    try:
        ticker = asset['yfinance_ticker']
        name = asset['name']
        print(f"Traitement de {name} ({ticker})")
        
        # Télécharger les 100 dernières barres de 15 minutes
        donnees = yf.download(ticker, period="15d", interval="15m")

        # Télécharger les données OHLCV toutes les minutes         
        # donnees = yf.download(ticker, start="2026-03-31", end="2026-04-02", interval="15m")

        print(type(donnees))

        # 1. On aplatit le MultiIndex (si yfinance a créé des colonnes doubles comme ['Open', 'ZSIL.SW'])
        donnees.columns = donnees.columns.get_level_values(0)

        # 2. On supprime les lignes vides (le dernier jour peut être incomplet et contenir du texte/NaN)
        donnees = donnees.dropna()

        # 3. Optionnel : On s'assure que tout est bien au format numérique
        donnees = donnees.astype(float)

        # Afficher les 5 premières lignes du tableau (avec Date, Open, High, Low, Close, Volume)
        print(donnees.head())

        # Si vous voulez l'exporter en CSV :
        # donnees.to_csv(f'{ticker}_history_1.csv')

        # afficher les données avec matplotlib
        config_export = {
            'fname': f'data/april/chart_{ticker}.png', 
            'dpi': 300,                # Haute résolution (standard pro)
            'bbox_inches': 'tight'      # Supprime les bordures blanches inutiles
        }
        mpf.plot(donnees, type='candle', style='charles', title=f'{ticker} - {name}', volume=True, savefig=config_export)
    except Exception as e:
        print(f"Erreur lors du traitement de {asset['name']} ({ticker}): {e}")
        
        
    