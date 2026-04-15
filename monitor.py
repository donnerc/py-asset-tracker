import threading
import time

from triggers import monitor_price
from watchlist import commodities, cryptos, etf_sw, tracked_eu, tracked_stocks_us, tracked_sw

WATCHLIST_GROUPS = {
    "tracked_stocks_us": tracked_stocks_us,
    "tracked_eu": tracked_eu,
    "tracked_sw": tracked_sw,
    "etf_sw": etf_sw,
    "commodities": commodities,
    "cryptos": cryptos,
}


def iter_tracked_assets():
    for group_name, assets in WATCHLIST_GROUPS.items():
        for ticker_symbol, price_range in assets.items():
            low_price, high_price = price_range
            yield group_name, ticker_symbol, low_price, high_price


def start_monitoring():
    threads = []

    for group_name, ticker_symbol, low_price, high_price in iter_tracked_assets():
        thread = threading.Thread(
            target=monitor_price,
            args=(ticker_symbol, low_price, high_price),
            daemon=True,
            name=f"monitor-{ticker_symbol}",
        )
        thread.start()
        threads.append(thread)
        print(
            f"Thread lancé pour {ticker_symbol} depuis {group_name} "
            f"avec cible {low_price} - {high_price}"
        )

    return threads


if __name__ == "__main__":
    threads = start_monitoring()
    print(f"{len(threads)} thread(s) de surveillance démarré(s). Ctrl+C pour quitter.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Arrêt du monitoring demandé.")
