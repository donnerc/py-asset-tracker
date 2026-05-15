import curses
import yfinance as yf
import time
import threading
from datetime import datetime

# Configuration
TICKERS = ['MU', 'AVGO', 'NVDA', 'INTC', 'AMD', 'PLUG', 'MAR', 'TSM', 'GOOG', 'RGTI', 'TSLA', 'QCOM']
INTERVAL = 10

class StockMonitor:
    def __init__(self, tickers):
        self.tickers = tickers
        self.history = []
        self.scroll_offset = 0
        self.running = True
        self.data_lock = threading.Lock()
        self.last_update = "N/A"

    def fetch_data(self):
        while self.running:
            new_rows = []
            timestamp = datetime.now().strftime('%H:%M:%S')
            for symbol in self.tickers:
                if not self.running:
                    break
                try:
                    t = yf.Ticker(symbol)
                    info = t.fast_info
                    current = info['last_price']
                    open_price = info['open']
                    
                    if current is None or open_price is None:
                        # Fallback to .info if fast_info is incomplete
                        details = t.info
                        current = details.get('currentPrice') or details.get('regularMarketPrice')
                        open_price = details.get('regularMarketOpen') or details.get('open')

                    if current is not None and open_price is not None:
                        change = current - open_price
                        p_change = (change / open_price) * 100 if open_price else 0
                        
                        new_rows.append({
                            'time': timestamp,
                            'ticker': symbol,
                            'price': current,
                            'open': open_price,
                            'change': change,
                            'p_change': p_change
                        })
                except Exception:
                    pass
            
            if new_rows:
                with self.data_lock:
                    # Add to history (newest at bottom)
                    self.history.extend(new_rows)
                    self.last_update = timestamp
            
            # Sleep in small increments to respond quickly to shutdown
            for _ in range(INTERVAL * 2):
                if not self.running:
                    break
                time.sleep(0.5)

    def draw_ui(self, stdscr):
        # Setup curses
        curses.curs_set(0)
        stdscr.nodelay(1)
        curses.start_color()
        # Pair 1: Green on Black, Pair 2: Red on Black
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        
        # Start fetch thread
        fetch_thread = threading.Thread(target=self.fetch_data, daemon=True)
        fetch_thread.start()
        
        while self.running:
            try:
                stdscr.erase()
                height, width = stdscr.getmaxyx()
                
                # Header
                header = f"{'Heure':<10} | {'Ticker':<8} | {'Prix':<10} | {'Open':<10} | {'Change':<10} | {'%':<8}"
                # Ensure header doesn't exceed width
                header = header[:width-1]
                stdscr.addstr(0, 0, header, curses.A_BOLD | curses.A_REVERSE)
                stdscr.addstr(1, 0, "-" * min(width-1, len(header)))

                # Rows
                with self.data_lock:
                    visible_rows = height - 4 # Header(1), Sep(1), Footer(1), Spare(1)
                    num_history = len(self.history)
                    
                    if num_history > 0 and visible_rows > 0:
                        # scroll_offset = 0 means we show the very end of history
                        # max_scroll = num_history - visible_rows
                        max_scroll = max(0, num_history - visible_rows)
                        
                        # Clamp scroll_offset
                        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))
                        
                        start_idx = max(0, num_history - visible_rows - self.scroll_offset)
                        end_idx = min(num_history, start_idx + visible_rows)
                        
                        for i, idx in enumerate(range(start_idx, end_idx)):
                            row = self.history[idx]
                            color = curses.color_pair(1) if row['change'] >= 0 else curses.color_pair(2)
                            
                            line = f"{row['time']:<10} | {row['ticker']:<8} | {row['price']:<10.2f} | {row['open']:<10.2f} | {row['change']:<10.2f} | {row['p_change']:>7.2f}%"
                            line = line[:width-1]
                            try:
                                stdscr.addstr(i + 2, 0, line, color)
                            except curses.error:
                                pass

                # Footer
                footer = f" [Q] Quit | [Up/Down/PgUp/PgDn] Scroll | History: {num_history} | Offset: {self.scroll_offset} | Last: {self.last_update}"
                try:
                    stdscr.addstr(height - 1, 0, footer[:width-1], curses.A_DIM)
                except curses.error:
                    pass

                stdscr.refresh()
                
                # Handle input
                ch = stdscr.getch()
                if ch == ord('q') or ch == ord('Q'):
                    self.running = False
                elif ch == curses.KEY_UP:
                    self.scroll_offset += 1
                elif ch == curses.KEY_DOWN:
                    self.scroll_offset -= 1
                elif ch == curses.KEY_PPAGE: # PgUp
                    self.scroll_offset += visible_rows
                elif ch == curses.KEY_NPAGE: # PgDn
                    self.scroll_offset -= visible_rows
                
            except Exception:
                # Basic error handling to prevent crash in loop
                pass
            
            time.sleep(0.1)

if __name__ == "__main__":
    monitor = StockMonitor(TICKERS)
    try:
        curses.wrapper(monitor.draw_ui)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.running = False
