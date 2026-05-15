
import tempfile
import matplotlib.pyplot as plt
import yfinance as yf


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


def build_price_chart_png(ticker_symbol, interval, candles_count=80, handle=None):
    """Builds a PNG chart for the last N candles with MM200, MM50 and directional performance."""
    
    def default_handle(data):
        pass
    
    if handle is None:
        handle = default_handle
    
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

    fig, (ax, ax_vol) = plt.subplots(
        2, 1, figsize=(10, 5.8), gridspec_kw={"height_ratios": [3, 1]}, sharex=True
    )

    for i, (_, row) in enumerate(candles.iterrows()):
        open_price = float(row["Open"])
        high_price = float(row["High"])
        low_price = float(row["Low"])
        close_price = float(row["Close"])
        color = "#2ca02c" if close_price >= open_price else "#d62728"

        ax.vlines(i, low_price, high_price, color=color, linewidth=1.2)
        ax.vlines(i, open_price, close_price, color=color, linewidth=6)

    # Volume bars
    for i, (_, row) in enumerate(candles.iterrows()):
        color = "#2ca02c" if float(row["Close"]) >= float(row["Open"]) else "#d62728"
        ax_vol.bar(i, float(row["Volume"]), color=color, width=0.8, alpha=0.7)

    x_values = list(range(len(candles)))
    ax.plot(x_values, candles["SMA200"], color="green", linewidth=1.8, label="MM200")
    ax.plot(x_values, candles["SMA50"], color="orange", linewidth=1.8, label="MM50")

    sma200_last = candles["SMA200"].dropna()
    if not sma200_last.empty:
        sma200_value = float(sma200_last.iloc[-1])
        ax.text(
            len(candles) - 1 + 0.6,
            sma200_value,
            f"{sma200_value:.2f}",
            color="green",
            fontsize=9,
            va="center",
            ha="left",
            fontweight="bold",
        )

    sma50_last = candles["SMA50"].dropna()
    if not sma50_last.empty:
        sma50_value = float(sma50_last.iloc[-1])
        ax.text(
            len(candles) - 1 + 0.6,
            sma50_value,
            f"{sma50_value:.2f}",
            color="orange",
            fontsize=9,
            va="center",
            ha="left",
            fontweight="bold",
        )

    ax.set_xlim(-0.5, len(candles) - 1 + 3)

    lowest_point = float(candles["Low"].min())
    highest_point = float(candles["High"].max())
    first_close = float(candles["Close"].iloc[0])
    latest_close = float(candles["Close"].iloc[-1])

    if latest_close >= first_close:
        reference_price = lowest_point
        reference_text = "From low"
        reference_color = "#1f77b4"
    else:
        reference_price = highest_point
        reference_text = "From high"
        reference_color = "#d62728"

    performance_pct = (
        ((latest_close - reference_price) / reference_price) * 100
        if reference_price > 0
        else 0.0
    )

    ax.axhline(reference_price, color=reference_color, linestyle="--", linewidth=1, alpha=0.35)
    ax.text(
        0.01,
        0.80,
        f"{reference_text}: {performance_pct:+.2f}%\nActuel: {latest_close:.2f}  Min: {lowest_point:.2f}  Max: {highest_point:.2f}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "alpha": 0.75, "edgecolor": "lightgray"},
    )

    daily_intervals = {"1d", "5d", "1wk", "1mo", "3mo"}
    date_fmt = "%d/%m/%Y" if interval in daily_intervals else "%d/%m %H:%M"
    labels = [ts.strftime(date_fmt) for ts in candles.index]
    tick_step = max(1, len(labels) // 14)
    tick_positions = list(range(0, len(labels), tick_step))
    if tick_positions[-1] != len(labels) - 1:
        tick_positions.append(len(labels) - 1)

    ax_vol.set_xticks(tick_positions)
    ax_vol.set_xticklabels([labels[i] for i in tick_positions], rotation=45, ha="right")
    ax.set_title(f"{asset_name} ({ticker_symbol}) - {candles_count} dernières bougies ({interval})")
    ax.set_ylabel("Prix")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left")

    ax_vol.set_ylabel("Volume", fontsize=8)
    ax_vol.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{x/1e6:.1f}M" if x >= 1e6 else f"{x/1e3:.0f}K" if x >= 1e3 else str(int(x)))
    )
    ax_vol.grid(alpha=0.25)

    fig.tight_layout()

    with tempfile.NamedTemporaryFile(prefix=f"{ticker_symbol}_", suffix=".png", delete=False) as tmp_file:
        output_path = tmp_file.name

    fig.savefig(output_path, dpi=120)
    plt.close(fig)
    
    charts_infos = {
        "ticker": ticker_symbol,
        "asset_name": asset_name,
        "interval": interval,
        "candles_count": candles_count,
        "latest_close": latest_close,
        "performance_pct": performance_pct,
        "mm200": sma200_value if not sma200_last.empty else None,
        "mm50": sma50_value if not sma50_last.empty else None,
        "chart_path": output_path,
    }
    
    handle(charts_infos)
    
    return output_path

