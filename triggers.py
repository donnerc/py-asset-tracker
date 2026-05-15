
import os
import time
import requests

import yfinance as yf

from charts import build_price_chart_png

from dotenv import load_dotenv

load_dotenv()


def send_trigger_charts(ticker_symbol):
    for interval in ("4h", "1h", "5m", "1m", "1d"):
        chart_path = build_price_chart_png(ticker_symbol, interval=interval, candles_count=100)
        if chart_path:
            send_telegram_photo(chart_path, f"{ticker_symbol} - 100 bougies ({interval})")


def send_telegram_message(message):
    token = os.getenv("TELEGRAM_BOT_SECRET_TOKEN")
    chat_id = os.getenv("TELEGRAM_BOT_CHAT_ID")

    if not token or not chat_id:
        print("Variables Telegram manquantes dans .env")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"Erreur envoi Telegram: {error}")


def send_telegram_photo(image_path, caption):
    token = os.getenv("TELEGRAM_BOT_SECRET_TOKEN")
    chat_id = os.getenv("TELEGRAM_BOT_CHAT_ID")

    if not token or not chat_id:
        print("Variables Telegram manquantes dans .env")
        return

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    payload = {
        "chat_id": chat_id,
        "caption": caption,
    }

    try:
        with open(image_path, "rb") as photo_file:
            files = {"photo": (os.path.basename(image_path), photo_file, "image/png")}
            response = requests.post(url, data=payload, files=files, timeout=15)
            response.raise_for_status()
    except (OSError, requests.RequestException) as error:
        print(f"Erreur envoi image Telegram: {error}")
    finally:
        try:
            os.remove(image_path)
        except OSError:
            pass

def monitor_price(ticker_symbol, low_price, high_price):
    ticker = yf.Ticker(ticker_symbol)
    alert_sent = False
    
    print(f"Surveillance de {ticker_symbol}... Cible : {low_price} - {high_price}")
    
    while True:
        # Récupère le dernier prix (intervalle 1m pour être le plus frais possible)
        data = ticker.history(period='1d', interval='1m')
        if not data.empty:
            current_price = data['Close'].iloc[-1]
            print(f"Prix actuel de {ticker_symbol} : {current_price:.4f}")

            if current_price >= high_price and not alert_sent:
                print(f"⚠️ TRIGGER ! {ticker_symbol} a atteint {current_price:.4f}")
                print('\a')  # Son d'alerte (peut ne pas fonctionner sur tous les systèmes)
                trigger_message = (
                    f"🟢⬆️ TRIGGER: {ticker_symbol} a atteint {current_price:.4f} "
                    f"(cible {high_price:.4f})"
                )
                send_telegram_message(trigger_message)
                send_trigger_charts(ticker_symbol)
                alert_sent = True
                
            if current_price <= low_price and not alert_sent:
                print(f"⚠️ TRIGGER ! {ticker_symbol} a atteint {current_price:.4f}")
                print('\a')  # Son d'alerte (peut ne pas fonctionner sur tous les systèmes)
                trigger_message = (
                    f"🔴⬇️ TRIGGER: {ticker_symbol} a atteint {current_price:.4f} "
                    f"(cible {low_price:.4f})"
                )
                send_telegram_message(trigger_message)
                send_trigger_charts(ticker_symbol)
                alert_sent = True

            if current_price > low_price and current_price < high_price:
                alert_sent = False
                
        
        # Attendre avant la prochaine vérification
        time.sleep(20)


import sys

if __name__ == "__main__":
    argv = sys.argv[1:]
    if len(argv) != 3:
        print("Usage: python triggers.py <TICKER> <LOW_PRICE> <HIGH_PRICE>")
        sys.exit(1)
    ticker_symbol = argv[0]
    low_price = float(argv[1])
    high_price = float(argv[2])
    monitor_price(ticker_symbol, low_price, high_price)
