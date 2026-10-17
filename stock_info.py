#!/usr/bin/env python3
"""
CMPE 285 - HW6 Part 1: Python Finance Info

Enter a stock symbol and the program prints:
    current date and time
    company name (SYMBOL)
    price  value-change  (percent-change)

Usage:
    python3 stock_info.py                 interactive, type q to quit
    python3 stock_info.py ADBE AAPL       look up each symbol, then exit

Data comes from Yahoo Finance through the yfinance library.
"""

from __future__ import annotations

import argparse
import logging
import math
import re
import socket
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, TextIO

YAHOO_HOST = "query2.finance.yahoo.com"
CACHE_SECONDS = 30
QUIT_COMMANDS = {"Q", "QUIT", "EXIT"}

# Tickers like ADBE, BRK-B, BRK.B, ^GSPC (index), EURUSD=X (currency)
TICKER_RE = re.compile(r"[A-Z0-9^][A-Z0-9.\-=^]{0,11}")


# ------------------------------------------------------------------ errors
class QuoteError(Exception):
    """Any problem we can explain to the user in one line."""


class BadSymbolError(QuoteError):
    pass


class ConnectionProblem(QuoteError):
    pass


class ProviderError(QuoteError):
    pass


# ------------------------------------------------------------------ model
@dataclass(frozen=True)
class Quote:
    symbol: str
    company: str
    price: float
    prev_close: float

    @property
    def change(self) -> float:
        return self.price - self.prev_close

    @property
    def change_pct(self) -> float:
        return 0.0 if self.prev_close == 0 else self.change / self.prev_close * 100


def clean_symbol(text: str) -> str:
    """Uppercase and check the user's input before using the network."""
    symbol = (text or "").strip().upper()
    if not symbol:
        raise BadSymbolError("Please type a stock symbol, for example ADBE.")
    if not TICKER_RE.fullmatch(symbol):
        raise BadSymbolError(f"'{text.strip()}' is not a valid stock symbol format.")
    return symbol


def internet_available(host: str = YAHOO_HOST, port: int = 443, timeout: float = 3.0) -> bool:
    """True if we can open a connection to Yahoo Finance (covers DNS, Wi-Fi off, firewall)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _as_price(value) -> float | None:
    """Turn a value from the API into a positive float, or None if it is unusable."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


# ------------------------------------------------------------------ data source
class YahooQuoteService:
    """
    Gets quotes from Yahoo Finance.

    Price = latest close in the last 5 trading days (today's live price while the
    market is open); previous close = the close before that.
    Results are cached briefly so repeating a symbol does not hit Yahoo's rate limit.
    """

    def __init__(
        self,
        cache_seconds: float = CACHE_SECONDS,
        is_online: Callable[[], bool] = internet_available,
        clock: Callable[[], float] = time.monotonic,
        yf_module=None,
    ):
        self.cache_seconds = cache_seconds
        self.is_online = is_online
        self.clock = clock
        self._yf = yf_module
        self._cache: dict[str, tuple[float, Quote]] = {}
        logging.getLogger("yfinance").setLevel(logging.CRITICAL)  # we print our own messages

    def quote(self, symbol: str) -> Quote:
        saved = self._cache.get(symbol)
        if saved and self.clock() - saved[0] < self.cache_seconds:
            return saved[1]
        result = self._download(symbol)
        self._cache[symbol] = (self.clock(), result)
        return result

    def _library(self):
        if self._yf is None:
            try:
                import yfinance
            except ImportError as exc:
                raise ProviderError("yfinance is not installed. Run: pip install yfinance") from exc
            self._yf = yfinance
        return self._yf

    def _download(self, symbol: str) -> Quote:
        yf = self._library()
        if not self.is_online():
            raise ConnectionProblem("No network connection to Yahoo Finance. Check your internet and try again.")

        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(period="5d", auto_adjust=False)
        except Exception as exc:
            if "RateLimit" in type(exc).__name__:
                raise ProviderError("Yahoo Finance is limiting requests. Wait a minute and try again.") from exc
            if isinstance(exc, OSError):
                raise ConnectionProblem("The connection to Yahoo Finance failed. Please try again.") from exc
            raise ProviderError(f"Yahoo Finance returned an error ({type(exc).__name__}).") from exc

        closes = self._closes(history)
        if len(closes) < 2:
            # yfinance returns empty data both for unknown symbols and for a dropped
            # connection, so check the network again before blaming the symbol.
            if not self.is_online():
                raise ConnectionProblem("Lost the network connection. Please try again.")
            raise BadSymbolError(f"No market data found for '{symbol}'. Check the symbol and try again.")

        return Quote(symbol, self._company(ticker, symbol), closes[-1], closes[-2])

    @staticmethod
    def _closes(history) -> list[float]:
        if history is None or getattr(history, "empty", True):
            return []
        try:
            values = list(history["Close"])
        except (KeyError, TypeError):
            return []
        return [p for p in (_as_price(v) for v in values) if p is not None]

    @staticmethod
    def _company(ticker, symbol: str) -> str:
        try:
            info = ticker.info or {}
            return info.get("longName") or info.get("shortName") or symbol
        except Exception:
            return symbol  # name is optional; still show the price


# ------------------------------------------------------------------ output
def render(quote: Quote, when: datetime) -> str:
    return (
        f"{when.strftime('%a %b %d %H:%M:%S %Z %Y')}\n"
        f"{quote.company} ({quote.symbol})\n"
        f"{quote.price:.2f} {quote.change:+.2f} ({quote.change_pct:+.2f}%)"
    )


class StockApp:
    def __init__(self, service, out: TextIO = sys.stdout,
                 now: Callable[[], datetime] = lambda: datetime.now().astimezone()):
        self.service = service
        self.out = out
        self.now = now

    def say(self, text: str = "") -> None:
        print(text, file=self.out)

    def show(self, text: str) -> bool:
        try:
            self.say(render(self.service.quote(clean_symbol(text)), self.now()))
            return True
        except QuoteError as err:
            self.say(f"Error: {err}")
        except Exception as err:  # never crash on something unexpected
            self.say(f"Error: something unexpected happened ({type(err).__name__}).")
        return False

    def batch(self, symbols: list[str]) -> None:
        for text in symbols:
            self.say("\nPlease enter a symbol:")
            self.say(text)
            self.show(text)

    def interactive(self, ask: Callable[[str], str] = input) -> None:
        self.say("Stock Info - type q to quit.")
        while True:
            try:
                text = ask("\nPlease enter a symbol:\n")
            except (EOFError, KeyboardInterrupt):
                self.say("\nGoodbye.")
                return
            if text.strip().upper() in QUIT_COMMANDS:
                self.say("Goodbye.")
                return
            self.show(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show a live stock quote from Yahoo Finance.")
    parser.add_argument("symbols", nargs="*", help="symbols to look up; leave empty for interactive mode")
    args = parser.parse_args(argv)

    app = StockApp(YahooQuoteService())
    try:
        if args.symbols:
            app.batch(args.symbols)
        else:
            app.interactive()
    except KeyboardInterrupt:
        print("\nGoodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

