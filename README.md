# CMPE 285 HW6 – Python Finance Info

**Shefali Saini** · Student ID 018281848 · CMPE 285, Fall 2026

A Python command-line program that takes a stock symbol and shows live stock information from Yahoo Finance:

- Current date and time
- Full company name
- Stock price
- Value change (+ for increase, - for decrease)
- Percentage change (+ for increase, - for decrease)

## Example

```
Stock Info - type q to quit.

Please enter a symbol:
ADBE
Sat Oct 17 10:22:49 PDT 2026
Adobe Inc. (ADBE)
245.20 -6.47 (-2.57%)

Please enter a symbol:
ZZZZZZ
Error: No market data found for 'ZZZZZZ'. Check the symbol and try again.

Please enter a symbol:
AA PL
Error: 'AA PL' is not a valid stock symbol format.

Please enter a symbol:
q
Goodbye.
```

## Requirements

- Python 3.9 or newer
- Internet connection
- [`yfinance`](https://pypi.org/project/yfinance/) (installed automatically by `run.sh`)

## How to run

macOS / Linux:

```bash
git clone <this-repo-url>
cd <repo-folder>
chmod +x run.sh        # first time only
```

| Command | What it does |
| --- | --- |
| `./run.sh` | Interactive mode: type one symbol at a time, `q` to quit |
| `./run.sh test` | Runs ADBE, AAPL, ZZZZZZ (does not exist) and `AA PL` (bad format), then exits |
| `./run.sh ADBE AAPL MSFT` | Looks up the given symbols, then exits |

The first run creates a Python virtual environment (`.venv`) and installs `yfinance`.

Windows (or without `run.sh`):

```bash
pip install yfinance
python stock_info.py
python stock_info.py ADBE AAPL
```

## Unit tests

```bash
python3 -m unittest -v test_stock_info
```

14 tests cover symbol validation, output format, no network, unknown symbols, missing prices, rate limiting, dropped connections, missing company names, caching, and the batch and interactive modes. They use a fake data source, so they run without internet.

## Error handling

| Situation | What the program does |
| --- | --- |
| No network | Checks the connection to Yahoo (3 s timeout) before each lookup and shows a clear message |
| Connection drops mid-request | Checks the network again before blaming the symbol |
| Badly formatted symbol | Rejected by a format check before any network call |
| Symbol does not exist | "No market data found" message |
| Rate limit or API error | Reported as a provider error; the program keeps running |
| Company name missing | Shows the symbol instead, still prints the price |
| Empty input, Ctrl+C, Ctrl+D | Asks again, or exits cleanly |

The program never crashes on bad input; every error is shown as a one-line message and you can enter another symbol.

## Design

| Part | Responsibility |
| --- | --- |
| `clean_symbol()` | Normalizes input (trim, uppercase) and validates the format |
| `YahooQuoteService` | Gets the data. Price = latest close in the last 5 trading days (the live price while the market is open); previous close = the one before. Caches each quote for 30 seconds to avoid Yahoo's rate limit |
| `Quote` | Data class that calculates the change and percent change |
| `render()` | Formats the output like the assignment example |
| `StockApp` | Runs interactive or command-line mode |
| `BadSymbolError`, `ConnectionProblem`, `ProviderError` | Error types, so each failure gets a specific message |

## Project files

```
stock_info.py        main program
run.sh               setup and run script
test_stock_info.py   unit tests
README.md            this file
```

## Notes

Stock data comes from Yahoo Finance through the unofficial `yfinance` library and is for educational use only. It is not financial advice.
