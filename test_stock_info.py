"""Unit tests for stock_info.py. Run: python3 -m unittest -v test_stock_info"""

import io
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import stock_info as si


class FakeHistory:
    """Stands in for the pandas DataFrame that yfinance returns."""

    def __init__(self, closes):
        self._closes = closes
        self.empty = not closes

    def __getitem__(self, column):
        return self._closes


def fake_yf(closes=(108.64, 109.24), name="Adobe Inc.", error=None):
    ticker = mock.MagicMock()
    ticker.history.return_value = FakeHistory(list(closes))
    ticker.info = {"longName": name}
    yf = mock.MagicMock()
    if error:
        yf.Ticker.side_effect = error
    else:
        yf.Ticker.return_value = ticker
    return yf


class SymbolTests(unittest.TestCase):
    def test_cleans_input(self):
        self.assertEqual(si.clean_symbol("  adbe "), "ADBE")
        self.assertEqual(si.clean_symbol("brk-b"), "BRK-B")
        self.assertEqual(si.clean_symbol("^gspc"), "^GSPC")

    def test_rejects_empty_and_bad_format(self):
        for bad in ("", "   ", "AA PL", "AAPL!", "-ABC"):
            with self.assertRaises(si.BadSymbolError):
                si.clean_symbol(bad)


class RenderTests(unittest.TestCase):
    def test_matches_assignment_example(self):
        pdt = timezone(timedelta(hours=-7), "PDT")
        when = datetime(2016, 10, 10, 17, 23, 48, tzinfo=pdt)
        quote = si.Quote("ADBE", "Adobe Systems Incorporated", 109.24, 108.64)
        self.assertEqual(
            si.render(quote, when),
            "Mon Oct 10 17:23:48 PDT 2016\nAdobe Systems Incorporated (ADBE)\n109.24 +0.60 (+0.55%)",
        )

    def test_drop_shows_minus_signs(self):
        quote = si.Quote("X", "X Corp", 90.0, 100.0)
        self.assertTrue(si.render(quote, datetime.now().astimezone()).endswith("90.00 -10.00 (-10.00%)"))


class ServiceTests(unittest.TestCase):
    def service(self, yf, online=True, clock=lambda: 0.0):
        return si.YahooQuoteService(is_online=lambda: online, clock=clock, yf_module=yf)

    def test_valid_symbol(self):
        quote = self.service(fake_yf()).quote("ADBE")
        self.assertEqual(quote.company, "Adobe Inc.")
        self.assertAlmostEqual(quote.price, 109.24)
        self.assertAlmostEqual(quote.change, 0.60, places=2)

    def test_no_network(self):
        with self.assertRaises(si.ConnectionProblem):
            self.service(fake_yf(), online=False).quote("ADBE")

    def test_unknown_symbol(self):
        with self.assertRaises(si.BadSymbolError):
            self.service(fake_yf(closes=())).quote("ZZZZZZ")

    def test_ignores_missing_prices(self):
        with self.assertRaises(si.BadSymbolError):
            self.service(fake_yf(closes=(float("nan"), 50.0))).quote("ODD")

    def test_rate_limit(self):
        class YFRateLimitError(Exception):
            pass
        with self.assertRaises(si.ProviderError):
            self.service(fake_yf(error=YFRateLimitError("too many"))).quote("ADBE")

    def test_connection_dropped_during_request(self):
        with self.assertRaises(si.ConnectionProblem):
            self.service(fake_yf(error=ConnectionError("reset"))).quote("ADBE")

    def test_missing_company_name_falls_back_to_symbol(self):
        quote = self.service(fake_yf(name=None)).quote("ADBE")
        self.assertEqual(quote.company, "ADBE")

    def test_cache_avoids_second_request(self):
        yf = fake_yf()
        times = iter([0.0, 10.0, 100.0, 100.0])  # save, check, check, save
        service = self.service(yf, clock=lambda: next(times))
        service.quote("ADBE")   # downloads
        service.quote("ADBE")   # 10 s later: cached
        service.quote("ADBE")   # 100 s later: downloads again
        self.assertEqual(yf.Ticker.call_count, 2)


class AppTests(unittest.TestCase):
    def test_batch_keeps_going_after_errors(self):
        out = io.StringIO()
        app = si.StockApp(si.YahooQuoteService(is_online=lambda: True, yf_module=fake_yf()), out=out)
        app.batch(["ADBE", "AA PL"])
        text = out.getvalue()
        self.assertIn("Adobe Inc. (ADBE)", text)
        self.assertIn("Error: 'AA PL' is not a valid stock symbol format.", text)

    def test_interactive_quits(self):
        out = io.StringIO()
        app = si.StockApp(mock.MagicMock(), out=out)
        app.interactive(ask=lambda prompt: "q")
        self.assertIn("Goodbye.", out.getvalue())


if __name__ == "__main__":
    unittest.main()