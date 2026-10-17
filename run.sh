#!/usr/bin/env bash

# How to run:

# ./run.sh - Type one stock symbol and press Enter. Keep entering symbols, and type q to quit.

# ./run.sh test - Runs a test for two valid symbols, one symbol that does not exist, one badly formatted symbol.

# ./run.sh ADBE AAPL MSFT - Runs the symbols you give, one after another, then exits.


set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "First run: setting up Python environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q --disable-pip-version-check yfinance

if [ "$1" = "test" ]; then
  echo "Running test inputs: ADBE, AAPL, ZZZZZZ (does not exist), AA PL (bad format)"
  python3 stock_info.py ADBE AAPL ZZZZZZ "AA PL"
else
  python3 stock_info.py "$@"
fi