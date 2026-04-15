
import os
import time
import tempfile

import matplotlib.pyplot as plt
import requests
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()


def _get_history_period(interval):
    if interval == "1m":
        return "7d"
    if interval in {"2m", "5m", "15m", "30m", "60m", "90m", "1h"}:
        return "60d"
    return "730d"


def _get_asset_display_name(ticker, ticker_symbol):
    try:
        info = ticker.info or {}
        return (
            info.get("longName")
            or info.get("shortName")
            or info.get("displayName")
            or ticker_symbol
        )
    except Exception:
        return ticker_symbol


def build_price_chart_png(ticker_symbol, interval, candles_count=80):
    """Builds a PNG chart for the last N candles with MM200, MM50 and directional performance."""
    history_period = _get_history_period(interval)
    ticker = yf.Ticker(ticker_symbol)
    asset_name = _get_asset_display_name(ticker, ticker_symbol)
    data = ticker.history(period=history_period, interval=interval)
    if data.empty:
        print(f"Impossible de generer le graphique: aucune donnee {interval}.")
        return None

    required_history = max(candles_count + 200, 250)
    data = data.tail(required_history).copy()
    data["SMA200"] = data["Close"].rolling(window=200, min_periods=200).mean()
    data["SMA50"] = data["Close"].rolling(window=50, min_periods=50).mean()

    candles = data.tail(candles_count)
    if candles.empty:
        print("Impossible de generer le graphique: pas assez de points.")
        return None

    fig, ax = plt.subplots(figsize=(10, 4.8))

    for i, (_, row) in enumerate(candles.iterrows()):
        open_price = float(row["Open"])
        high_price = float(row["High"])
        low_price = float(row["Low"])
        close_price = float(row["Close"])
        color = "#2ca02c" if close_price >= open_price else "#d62728"

        ax.vlines(i, low_price, high_price, color=color, linewidth=1.2)
        ax.vlines(i, open_price, close_price, color=color, linewidth=6)

    x_values = list(range(len(candles)))
    ax.plot(x_values, candles["SMA200"], color="green", linewidth=1.8, label="MM200")
    ax.plot(x_values, candles["SMA50"], color="orange", linewidth=1.8, label="MM50")

    lowest_point = float(candles["Low"].min())
    highest_point = float(candles["High"].max())
    first_close = float(candles["Close"].iloc[0])
    latest_close = float(candles["Close"].iloc[-1])

    if latest_close >= first_close:
        reference_price = lowest_point
        reference_text = "Depuis le plus bas"
        reference_color = "#1f77b4"
    else:
        reference_price = highest_point
        reference_text = "Depuis le plus haut"
        reference_color = "#d62728"

    performance_pct = (
        ((latest_close - reference_price) / reference_price) * 100
        if reference_price > 0
        else 0.0
    )

    ax.axhline(reference_price, color=reference_color, linestyle="--", linewidth=1, alpha=0.35)
    ax.text(
        0.01,
        0.10,
        f"{reference_text}: {performance_pct:+.2f}%",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "alpha": 0.75, "edgecolor": "lightgray"},
    )

    labels = [ts.strftime("%d/%m %H:%M") for ts in candles.index]
    tick_step = max(1, len(labels) // 8)
    tick_positions = list(range(0, len(labels), tick_step))
    if tick_positions[-1] != len(labels) - 1:
        tick_positions.append(len(labels) - 1)

    ax.set_xticks(tick_positions)
    ax.set_xticklabels([labels[i] for i in tick_positions], rotation=30, ha="right")
    ax.set_title(f"{asset_name} ({ticker_symbol}) - {candles_count} dernières bougies ({interval})")
    ax.set_ylabel("Prix")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left")
    fig.tight_layout()

    with tempfile.NamedTemporaryFile(prefix=f"{ticker_symbol}_", suffix=".png", delete=False) as tmp_file:
        output_path = tmp_file.name

    fig.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path


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
                
        
        # Attendre 20 secondes avant la prochaine vérification
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
