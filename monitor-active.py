import curses
import yfinance as yf
import time
import threading
from datetime import datetime

# Configuration
TICKERS = ['MU', 'AVGO', 'NVDA', 'INTC', 'AMD', 'PLUG', 'AMAT', 'RXT', 'SMSN.IL', 'AAPL']
INTERVAL = 2

class StockMonitor:
    def __init__(self, tickers):
        self.tickers = tickers
        self.history = []  # List of dicts: {'time': '...', 'prices': {ticker: p}, 'changes': {ticker: c}}
        self.opens = {t: 0.0 for t in tickers}
        self.current_pcts = {t: 0.0 for t in tickers}
        self.current_prices = {t: 0.0 for t in tickers}
        self.scroll_offset = 0
        self.running = True
        self.data_lock = threading.Lock()
        self.last_update = "N/A"

    def fetch_data(self):
        while self.running:
            timestamp = datetime.now().strftime('%H:%M:%S')
            new_prices = {}
            new_changes = {}
            
            for symbol in self.tickers:
                if not self.running:
                    break
                try:
                    t = yf.Ticker(symbol)
                    info = t.fast_info
                    current = info['last_price']
                    open_p = info['open']
                    
                    if current is None or open_p is None:
                        details = t.info
                        current = details.get('currentPrice') or details.get('regularMarketPrice')
                        open_p = details.get('regularMarketOpen') or details.get('open')

                    if current is not None and open_p is not None:
                        change = current - open_p
                        p_change = (change / open_p) * 100 if open_p else 0
                        
                        new_prices[symbol] = current
                        new_changes[symbol] = change
                        
                        with self.data_lock:
                            self.opens[symbol] = open_p
                            self.current_pcts[symbol] = p_change
                            self.current_prices[symbol] = current
                except Exception:
                    pass
            
            if new_prices:
                with self.data_lock:
                    self.history.append({
                        'time': timestamp,
                        'prices': new_prices,
                        'changes': new_changes
                    })
                    self.last_update = timestamp
            
            # Wait for next interval
            for _ in range(INTERVAL * 2):
                if not self.running:
                    break
                time.sleep(0.5)

    def draw_ui(self, stdscr):
        curses.curs_set(0)
        stdscr.nodelay(1)
        curses.start_color()
        # Pair 1: Green, Pair 2: Red
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        
        fetch_thread = threading.Thread(target=self.fetch_data, daemon=True)
        fetch_thread.start()
        
        while self.running:
            try:
                stdscr.erase()
                height, width = stdscr.getmaxyx()
                
                with self.data_lock:
                    time_col_width = 10
                    col_width = max(12, (width - time_col_width) // len(self.tickers))
                    
                    # Row 0: Ticker Names
                    stdscr.addstr(0, 0, f"{'TICKER':<{time_col_width}}", curses.A_BOLD | curses.A_REVERSE)
                    for i, t in enumerate(self.tickers):
                        stdscr.addstr(0, time_col_width + i * col_width, f"| {t:<{col_width-2}}", curses.A_BOLD | curses.A_REVERSE)
                    
                    # Row 1: Open Prices
                    stdscr.addstr(1, 0, f"{'OPEN':<{time_col_width}}")
                    for i, t in enumerate(self.tickers):
                        stdscr.addstr(1, time_col_width + i * col_width, f"| {self.opens[t]:<{col_width-2}.2f}")
                        
                    # Row 2: Current % Change (Summary)
                    stdscr.addstr(2, 0, f"{'% CHANGE':<{time_col_width}}")
                    for i, t in enumerate(self.tickers):
                        pct = self.current_pcts[t]
                        color = curses.color_pair(1) if pct >= 0 else curses.color_pair(2)
                        stdscr.addstr(2, time_col_width + i * col_width, "| ")
                        stdscr.addstr(2, time_col_width + i * col_width + 2, f"{pct:<{col_width-4}.2f}%", color)

                    # Separator
                    stdscr.addstr(3, 0, "-" * min(width-1, time_col_width + len(self.tickers) * col_width))

                    # History Table
                    history_header_y = 4
                    visible_rows = height - history_header_y - 1
                    num_history = len(self.history)
                    
                    if num_history > 0 and visible_rows > 0:
                        max_scroll = max(0, num_history - visible_rows)
                        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))
                        
                        # Show latest by default (offset 0)
                        start_idx = max(0, num_history - visible_rows - self.scroll_offset)
                        end_idx = min(num_history, start_idx + visible_rows)
                        
                        for i, idx in enumerate(range(start_idx, end_idx)):
                            row = self.history[idx]
                            y = history_header_y + i
                            if y >= height - 1:
                                break
                            
                            stdscr.addstr(y, 0, f"{row['time']:<{time_col_width}}")
                            for j, t in enumerate(self.tickers):
                                price = row['prices'].get(t, 0.0)
                                change = row['changes'].get(t, 0.0)
                                color = curses.color_pair(1) if change >= 0 else curses.color_pair(2)
                                stdscr.addstr(y, time_col_width + j * col_width, "| ")
                                if price > 0:
                                    stdscr.addstr(y, time_col_width + j * col_width + 2, f"{price:<{col_width-4}.2f}", color)
                                else:
                                    stdscr.addstr(y, time_col_width + j * col_width + 2, f"{'---':<{col_width-4}}")

                # Footer
                footer = f" [Q] Quit | [Arrows/Pg] Scroll | Hist: {len(self.history)} | Last: {self.last_update}"
                try:
                    stdscr.addstr(height - 1, 0, footer[:width-1], curses.A_DIM)
                except curses.error:
                    pass

                stdscr.refresh()
                
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
